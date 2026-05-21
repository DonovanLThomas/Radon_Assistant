import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dateutil import parser as date_parser

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks",
]


def google_dependencies_available():
    try:
        import google.auth.transport.requests  # noqa: F401
        import google.oauth2.credentials  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def get_credentials():
    if not google_dependencies_available():
        raise RuntimeError(
            "Google API packages are missing. Run: pip install -r requirements.txt"
        )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            raise RuntimeError(
                f"Missing {CREDENTIALS_FILE.name}. Download it from Google Cloud OAuth credentials and place it in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=8080, open_browser=False)

    TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_service(api_name, api_version):
    from googleapiclient.discovery import build

    return build(api_name, api_version, credentials=get_credentials())


def list_calendar_events(max_results=5):
    service = get_service("calendar", "v3")

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=1)
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for event in events_result.get("items", []):
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date"))
        events.append({
            "summary": event.get("summary", "Untitled event"),
            "start": start,
        })
    return events


def list_tasks(max_results=8):
    service = get_service("tasks", "v1")

    tasklists_result = service.tasklists().list(maxResults=1).execute()
    tasklists = tasklists_result.get("items", [])
    if not tasklists:
        return []

    tasklist_id = tasklists[0]["id"]
    tasks_result = service.tasks().list(
        tasklist=tasklist_id,
        maxResults=max_results,
        showCompleted=False,
    ).execute()

    tasks = []
    for task in tasks_result.get("items", []):
        tasks.append({
            "id": task.get("id"),
            "tasklist_id": tasklist_id,
            "title": task.get("title", "Untitled task"),
            "due": task.get("due"),
        })
    return tasks


def create_task(title, due_date=None):
    service = get_service("tasks", "v1")

    tasklists_result = service.tasklists().list(maxResults=1).execute()
    tasklists = tasklists_result.get("items", [])
    if not tasklists:
        raise RuntimeError("No Google Tasks list found.")

    body = {"title": title}
    if due_date is not None:
        body["due"] = due_date.isoformat().replace("+00:00", "Z")

    created = service.tasks().insert(tasklist=tasklists[0]["id"], body=body).execute()
    return {
        "title": created.get("title", title),
        "due": created.get("due"),
    }


def delete_task(tasklist_id, task_id):
    service = get_service("tasks", "v1")
    service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()


def format_event_time(value):
    if not value:
        return "sometime"

    try:
        parsed = date_parser.isoparse(value)
    except (TypeError, ValueError):
        return value

    if "T" not in value:
        return parsed.strftime("%A")
    return parsed.astimezone().strftime("%I:%M %p").lstrip("0")


def format_task_due(value):
    if not value:
        return None

    try:
        parsed = date_parser.isoparse(value)
    except (TypeError, ValueError):
        return None

    return parsed.strftime("%A")


def save_debug_payload(name, payload):
    path = ROOT / f"{name}.debug.json"
    path.write_text(json.dumps(payload, indent=2))

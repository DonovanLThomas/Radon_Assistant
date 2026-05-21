import requests
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import time
from google_services import (
    create_task,
    delete_task,
    format_event_time,
    format_task_due,
    list_calendar_events,
    list_tasks,
)

VALID_STATES = ["idle", "listening", "thinking", "acting", "speaking", "error"]
assistant_state = "idle"
WEATHER_CACHE_SECONDS = 60
cached_weather = None
cached_weather_at = 0

def set_assistant_state(state):
    global assistant_state

    if state not in VALID_STATES:
        assistant_state = "error"
        print("Invalid assistnat state")
        return 
    assistant_state = state
    message = f"Radon state: {assistant_state}"
    print(message)

def get_time():
    now = datetime.now()
    formatted_time = now.strftime("%I:%M %p")
    return f"It's {formatted_time}, twin."

def show_message(text, weather=None):
    # Hook point for the direct Jetson display/avatar layer.
    return {"state": assistant_state, "message": text, "weather": weather}


def weather_condition(weather_code):
    if weather_code == 0:
        return "sunny"
    if weather_code in [1, 2, 3, 45, 48]:
        return "cloudy"
    if weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "rainy"
    if weather_code in [95, 96, 99]:
        return "stormy"
    return "cloudy"

def weather_message(user_prompt, weather):
    prompt = user_prompt.lower()
    temp = weather["current_temp"]
    feels_like = weather["feels_like"]
    high = weather["high_temp"]
    low = weather["low_temp"]
    rain_chance = weather["rain_chance"]
    wind = weather["wind_speed"]
    condition = weather["condition"]
    location = weather["location"]

    if any(word in prompt for word in ["jacket", "hoodie", "coat", "wear"]):
        if feels_like < 55:
            advice = "I'd wear a jacket."
        elif feels_like < 65:
            advice = "A light hoodie would be smart."
        else:
            advice = "You can probably skip the jacket."

        if rain_chance >= 40:
            advice += " Bring something for rain too."

        return f"{advice} It feels like {feels_like}°F in {location}, with a high of {high}° and low of {low}°."

    if any(word in prompt for word in ["umbrella", "rain", "raining", "wet"]):
        if rain_chance >= 50 or condition in ["rainy", "stormy"]:
            return f"Yeah, I'd bring an umbrella. Rain chance is {rain_chance}% in {location}."
        return f"Nah, rain looks low right now. {location} has a {rain_chance}% rain chance."

    if any(word in prompt for word in ["wind", "windy"]):
        return f"Wind is around {wind} mph in {location} right now."

    if any(word in prompt for word in ["cold", "hot", "temperature", "temp"]):
        return f"It's {temp}°F in {location} and feels like {feels_like}°F. Today's high is {high}° and the low is {low}°."

    return f"{location} is {temp}°F and feels like {feels_like}°F. High today is {high}°, low is {low}°, with a {rain_chance}% rain chance."


def show_weather(user_prompt=""):
    global cached_weather, cached_weather_at

    now = time.time()
    if cached_weather is not None and now - cached_weather_at < WEATHER_CACHE_SECONDS:
        return weather_message(user_prompt, cached_weather), cached_weather

    url = "https://api.open-meteo.com/v1/forecast?latitude=36.9741&longitude=-122.0308&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America/Los_Angeles&forecast_days=1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    current = data["current"]
    daily = data["daily"]

    current_temp = current["temperature_2m"]
    feels_like = current["apparent_temperature"]
    precipitation = current["precipitation"]
    weather_code = current["weather_code"]
    wind_speed = current["wind_speed_10m"]
    high_temp = daily["temperature_2m_max"][0]
    low_temp = daily["temperature_2m_min"][0]
    rain_chance = daily["precipitation_probability_max"][0]
    condition = weather_condition(weather_code)

    weather = {
        "location": "Santa Cruz",
        "condition": condition,
        "current_temp": current_temp,
        "feels_like": feels_like,
        "high_temp": high_temp,
        "low_temp": low_temp,
        "rain_chance": rain_chance,
        "precipitation": precipitation,
        "wind_speed": wind_speed,
        "weather_code": weather_code,
        "updated_at": datetime.now().isoformat(),
    }
    cached_weather = weather
    cached_weather_at = now
    return weather_message(user_prompt, weather), weather

def show_calendar():
    try:
        events = list_calendar_events()
    except Exception as error:
        return f"I couldn't reach Google Calendar yet: {error}"

    if not events:
        return "Your calendar looks clear for the next day."

    event_bits = []
    for event in events[:5]:
        event_bits.append(f"{event['summary']} at {format_event_time(event['start'])}")

    if len(event_bits) == 1:
        return f"You've got one calendar event: {event_bits[0]}."

    return f"You've got {len(event_bits)} calendar events coming up: " + "; ".join(event_bits) + "."


def show_tasks():
    try:
        tasks = list_tasks()
    except Exception as error:
        return f"I couldn't reach Google Tasks yet: {error}"

    if not tasks:
        return "You're clear. I don't see any open Google Tasks."

    task_bits = []
    for task in tasks[:5]:
        due = format_task_due(task.get("due"))
        if due:
            task_bits.append(f"{task['title']} due {due}")
        else:
            task_bits.append(task["title"])

    if len(task_bits) == 1:
        return f"You've got one task: {task_bits[0]}."

    return f"You've got {len(task_bits)} open tasks: " + "; ".join(task_bits) + "."


def task_title_from_prompt(user_prompt, args=None):
    if args and args.get("title"):
        return args["title"].strip()

    prompt = user_prompt.strip()
    lowered = prompt.lower()
    starters = [
        "add a task to",
        "add task to",
        "create a task to",
        "make a task to",
        "remind me to",
        "add a task",
        "add task",
        "create task",
        "make task",
    ]

    title = prompt
    for starter in starters:
        if lowered.startswith(starter):
            title = prompt[len(starter):].strip()
            break

    for marker in [" tomorrow", " today", " tonight"]:
        index = title.lower().find(marker)
        if index != -1:
            title = title[:index].strip()

    return clean_task_title(title)


def clean_task_title(title):
    title = " ".join(title.strip().split())
    if title.lower().startswith("that i need to "):
        title = title[15:].strip()
    if title.lower().startswith("me to "):
        title = title[6:].strip()
    return title or "New task"


def task_due_from_prompt(user_prompt, args=None):
    if args and args.get("due") in ["today", "tonight", "tomorrow"]:
        prompt = args["due"]
    else:
        prompt = user_prompt.lower()

    now = datetime.now().astimezone()

    if "tomorrow" in prompt:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    if "today" in prompt or "tonight" in prompt:
        return now.replace(hour=23, minute=59, second=0, microsecond=0)
    return None


def add_task(user_prompt, args=None):
    title = task_title_from_prompt(user_prompt, args)
    due = task_due_from_prompt(user_prompt, args)

    try:
        task = create_task(title, due)
    except Exception as error:
        return f"I couldn't add that Google Task yet: {error}"

    due_text = format_task_due(task.get("due"))
    if due_text:
        return f"Done. I added '{task['title']}' to your tasks for {due_text}."
    return f"Done. I added '{task['title']}' to your tasks."


def remove_task_title_from_prompt(user_prompt, args=None):
    if args and args.get("title"):
        title = args["title"].strip()
        return clean_remove_task_title(title)

    prompt = user_prompt.strip()
    lowered = prompt.lower()
    starters = [
        "remove the task",
        "delete the task",
        "complete the task",
        "mark the task",
        "remove task",
        "delete task",
        "complete task",
        "mark task",
        "remove",
        "delete",
        "complete",
    ]

    title = prompt
    for starter in starters:
        if lowered.startswith(starter):
            title = prompt[len(starter):].strip()
            break

    if title.lower().startswith("to "):
        title = title[3:].strip()
    if title.lower().startswith("as done"):
        title = title[7:].strip()
    if title.lower().startswith("done"):
        title = title[4:].strip()

    return clean_remove_task_title(title)


def clean_remove_task_title(title):
    title = clean_task_title(title)
    if title.lower().startswith("my "):
        title = title[3:].strip()
    for suffix in [" task", " todo", " reminder"]:
        if title.lower().endswith(suffix):
            title = title[:-len(suffix)].strip()
    return title or "New task"


def task_match_score(query, task_title):
    query = query.lower().strip()
    task_title = task_title.lower().strip()
    if not query or not task_title:
        return 0
    if query == task_title:
        return 1
    if query in task_title or task_title in query:
        return 0.9
    return SequenceMatcher(None, query, task_title).ratio()


def remove_task(user_prompt, args=None):
    query = remove_task_title_from_prompt(user_prompt, args)

    try:
        tasks = list_tasks(max_results=20)
    except Exception as error:
        return f"I couldn't reach Google Tasks yet: {error}"

    if not tasks:
        return "You don't have any open tasks for me to remove."

    best_task = None
    best_score = 0
    for task in tasks:
        score = task_match_score(query, task["title"])
        if score > best_score:
            best_task = task
            best_score = score

    if best_task is None or best_score < 0.55:
        return f"I couldn't find a close task match for '{query}'."

    try:
        delete_task(best_task["tasklist_id"], best_task["id"])
    except Exception as error:
        return f"I couldn't remove that Google Task yet: {error}"

    return f"Done. I removed '{best_task['title']}' from your tasks."

def unknown():
    return "I'm not totally sure what you mean, twin. Right now I can help with time, weather, calendar, and tasks."

def control_display(state):
    pass

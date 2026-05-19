from datetime import datetime
from ui import update_ui
VALID_STATES = ["idle", "listening", "thinking", "acting", "speaking", "error"]

def set_assistant_state(state):
    global assistant_state

    if state not in VALID_STATES:
        assistant_state = "error"
        print("Invalid assistnat state")
        return 
    assistant_state = state
    message = f"Radon state: {assistant_state}"
    update_ui(assistant_state, message)

def get_time():
    now = datetime.now()
    formatted_time = now.strftime("%I:%M")
    return f"The time is {formatted_time}" 

def show_message(text):
    pass

def show_weather():
    pass

def show_calendar():
    pass

def unknown():
    return "Man I'm ngl I dont know what you talking about try again."

def control_display(state):
    pass


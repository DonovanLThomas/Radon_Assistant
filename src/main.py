import ollama
import json
import time
from tools import add_task, remove_task, set_assistant_state, get_time, show_calendar, show_tasks, unknown, show_message, show_weather


MODEL = "llama3.2:1b"
VALID_STATES = ["idle", "listening", "thinking", "acting", "speaking", "error"]
assistant_state = "idle"


def choose_function(user_prompt):
    response = ollama.chat(model=MODEL, messages=[
        {
            "role": "user",
            "content": f"""
                Classify the user message into one function and extract simple task arguments.

                Return JSON only in one of these shapes:
                {{"function":"show_weather","args":{{}}}}
                {{"function":"add_task","args":{{"title":"do psychology homework","due":"none"}}}}
                {{"function":"remove_task","args":{{"title":"psychology homework"}}}}

                Functions:
                get_time: current time, clock, hour, or what time it is.
                show_weather: weather, forecast, temperature, rain, wind, outside conditions, or clothing decisions based on weather.
                show_calendar: calendar, schedule, meetings, events, appointments, or asking what is planned.
                show_tasks: list tasks, todos, reminders, chores, or asking what tasks are open.
                add_task: add, create, make, or remind me about a task or todo.
                remove_task: remove, delete, complete, mark done, or clear a task or todo.
                unknown: anything else.

                Task args:
                - For add_task, set args.title to the actual task text only. Remove filler like "add task to". Lightly fix obvious speech or spelling mistakes.
                - For add_task, set args.due to "today", "tonight", "tomorrow", or "none".
                - For remove_task, set args.title to the task the user wants removed.
                - For all other functions, args must be {{}}.

                Examples:
                "should I wear a jacket today" -> show_weather
                "do I need an umbrella" -> show_weather
                "is it cold outside" -> show_weather
                "what time is it" -> get_time
                "what is on my calendar today" -> show_calendar
                "do I have any meetings" -> show_calendar
                "what tasks do I have" -> show_tasks
                "add a task to call mom tomorrow" -> {{"function":"add_task","args":{{"title":"call mom","due":"tomorrow"}}}}
                "add task to do my pysology homweork" -> {{"function":"add_task","args":{{"title":"do my psychology homework","due":"none"}}}}
                "remove my psychology homework task" -> {{"function":"remove_task","args":{{"title":"psychology homework"}}}}

                No Python. No explanations.

                User: {user_prompt}
                """
        }
    ],
    format="json",
    options={
        "num_ctx": 512,
        "num_predict": 96,
        "temperature": 0
    })

    raw_text = response["message"]["content"]
    print(raw_text)

    try:
        decision = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"function": "unknown", "args": {}}

    function_name = decision.get("function", "unknown")
    if function_name not in ["get_time", "show_weather", "show_calendar", "show_tasks", "add_task", "remove_task", "unknown"]:
        function_name = "unknown"

    args = decision.get("args", {})
    if not isinstance(args, dict):
        args = {}

    return {"function": function_name, "args": args}


def main():
    print("Radon is here for your needs.")
    while(True):
        set_assistant_state("listening")
        user_prompt = input("Talk to me twin\nIf you dippin just press Q\n")

        if(user_prompt == "Q" or user_prompt == "q"):
            print("Goodbye!\n")
            break

        set_assistant_state("thinking")
        decision = choose_function(user_prompt)
        function_name = decision["function"]
        args = decision["args"]
        set_assistant_state("acting")
        

        if function_name == "get_time":
            set_assistant_state("speaking")
            message = get_time()
            show_message(message)
            print(message)
            time.sleep(3)
        
        elif function_name == "show_weather":
            set_assistant_state("speaking")
            message, weather = show_weather(user_prompt)
            show_message(message, weather)
            print(message)
            time.sleep(3)

        elif function_name == "show_calendar":
            set_assistant_state("speaking")
            message = show_calendar()
            show_message(message)
            print(message)
            time.sleep(3)

        elif function_name == "show_tasks":
            set_assistant_state("speaking")
            message = show_tasks()
            show_message(message)
            print(message)
            time.sleep(3)

        elif function_name == "add_task":
            set_assistant_state("speaking")
            message = add_task(user_prompt, args)
            show_message(message)
            print(message)
            time.sleep(3)

        elif function_name == "remove_task":
            set_assistant_state("speaking")
            message = remove_task(user_prompt, args)
            show_message(message)
            print(message)
            time.sleep(3)
            
        else:
            set_assistant_state("speaking")
            message = unknown()
            show_message(message)
            print(message)
            time.sleep(3)



main()

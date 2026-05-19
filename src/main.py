import ollama
import json
import subprocess
from tools import set_assistant_state, get_time, unknown
from ui import update_ui

MODEL = "llama3.2:1b"
VALID_STATES = ["idle", "listening", "thinking", "acting", "speaking", "error"]
assistant_state = "idle"

def main():
    result = subprocess.run(['sh', './../scripts/full_screen.sh'], capture_output=True, text=True) 
    print("Radon is here for your needs.")
    while(True):
        set_assistant_state("listening")
        user_prompt = input("Talk to me twin\nIf you dippin just press Q\n")

        if(user_prompt == "Q" or user_prompt == "q"):
            print("Goodbye!\n")
            break

        set_assistant_state("thinking")

        response = ollama.chat(model=MODEL, messages=[
            {
                "role": "user",
                "content": f"""
                    You are Radon Assistant.

                    Your task is to choose exactly one function.

                    Available functions:
                    - get_time: use only if the user clearly asks for the current time. Examples: "what time is it", "tell me the time", "current time".
                    - unknown: use for greetings, random text, unclear messages, jokes, gibberish, or anything that does not clearly ask for the current time.

                    Rules:
                    - Return only JSON.
                    - If unsure, choose unknown.
                    - Do not guess.
                    - The function value must be exactly one of: "get_time", "unknown".
                    - Do not use markdown.
                    - Do not wrap the JSON in ```json.
                    - The first character of your response must be {{
                    - The last character of your response must be }}

                    Return format:
                    {{"function": "get_time", "args": {{}}}}

                    User message:
                    {user_prompt}
                    """
            }
        ])

        raw_text = response["message"]["content"]

        print(raw_text)
        set_assistant_state("acting")
        decision = json.loads(raw_text)
        function_name = decision["function"]
        

        if function_name == "get_time":
            set_assistant_state("speaking")
            print(get_time())

        if function_name == "unknown":
            set_assistant_state("speaking")
            print(unknown())



main()
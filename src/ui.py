import json
def update_ui(state, message):
    data = {
        "state": state,
        "message": message,
    }

    with open("../web/state.json", "w") as f:
        json.dump(data, f)
    
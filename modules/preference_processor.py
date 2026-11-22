def process_preferences(user_input):
    preferences = {
        "destination": user_input.get("destination"),
        "state": user_input.get("state"),
        "budget": user_input.get("budget"),
        "days": user_input.get("days", 2),
        "interests": user_input.get("interests", []),
        "daily_hours": user_input.get("daily_hours", 6),
        "travel_date": user_input.get("travel_date"),
        "people": user_input.get("people", 1)
    }

    if preferences["budget"] is not None:
        preferences["budget"] = float(preferences["budget"])

    preferences["days"] = int(preferences["days"])
    preferences["people"] = int(preferences["people"])

    if isinstance(preferences["interests"], str):
        preferences["interests"] = [
            item.strip()
            for item in preferences["interests"].split(",")
        ]

    return preferences
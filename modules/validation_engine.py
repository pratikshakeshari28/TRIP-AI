def validate_itinerary(
    itinerary,
    total_budget,
    user_budget,
    max_daily_hours=8
):
    errors = []

    if itinerary.empty:
        errors.append("No destinations found.")
        return {
            "valid": False,
            "errors": errors
        }

    if total_budget > user_budget:
        errors.append("Trip exceeds your budget.")

    daily_hours = itinerary.groupby("Day")[
        "Visiting Hours"
    ].sum()

    for day, hours in daily_hours.items():
        if hours > max_daily_hours:
            errors.append(
                f"{day} exceeds the daily visiting hours limit."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
from modules.itinerary_generator import generate_itinerary
from modules.budget_optimizer import calculate_trip_budget
from modules.validation_engine import validate_itinerary


def replan_trip(
    df,
    city,
    days,
    daily_hours,
    user_budget,
    hotel_per_night=1500,
    transport_per_day=500,
    food_per_day=500
):

    itinerary = generate_itinerary(
        df=df,
        city=city,
        days=days,
        daily_hours=daily_hours
    )

    budget = calculate_trip_budget(
        itinerary,
        hotel_per_night,
        transport_per_day,
        food_per_day
    )

    if "error" in budget:
        return {
            "itinerary": itinerary,
            "budget": budget,
            "validation": {
                "valid": False,
                "errors": ["Unable to generate itinerary."]
            }
        }

    total_cost = budget["Total Estimated Budget"]

    validation = validate_itinerary(
        itinerary=itinerary,
        total_budget=total_cost,
        user_budget=user_budget,
        max_daily_hours=daily_hours
    )

    return {
        "itinerary": itinerary,
        "budget": budget,
        "validation": validation
    }
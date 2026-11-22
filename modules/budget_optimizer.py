def calculate_trip_budget(
    itinerary,
    hotel_per_night=1500,
    transport_per_day=500,
    food_per_day=500
):
   

    if itinerary.empty:
        return {
            "error": "No itinerary available"
        }

    days = itinerary["Day"].nunique()

    entry_cost = itinerary["Entrance Fee"].sum()

    hotel_cost = max(0, days - 1) * hotel_per_night

    transport_cost = days * transport_per_day

    food_cost = days * food_per_day

    total_cost = (
        entry_cost
        + hotel_cost
        + transport_cost
        + food_cost
    )

    return {
        "Sightseeing": float(entry_cost),
        "Hotel": float(hotel_cost),
        "Transport": float(transport_cost),
        "Food": float(food_cost),
        "Total Estimated Budget": float(total_cost)
    }


def check_budget(total_cost, user_budget):

    remaining_budget = user_budget - total_cost

    return {
        "Estimated Cost": total_cost,
        "User Budget": user_budget,
        "Remaining Budget": remaining_budget,
        "Within Budget": remaining_budget >= 0
    }
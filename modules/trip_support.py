
from .booking_manager import get_booking


def answer_trip_query(question, booking_id):

    booking = get_booking(booking_id)

    if booking is None:
        return "Booking not found. Please check your Booking ID."

    question = question.lower()

    if "booking id" in question:
        return f"Your Booking ID is {booking['booking_id']}"

    elif "status" in question:
        return f"Booking Status: {booking['status']}"

    elif "budget" in question or "cost" in question:
        return f"Estimated Budget: Rs. {booking['estimated_budget']}"

    elif "hotel" in question:
        return f"Hotel: {booking['hotel']}"

    elif "transport" in question:
        return f"Transport: {booking['transport']}"

    elif "destination" in question:
        return f"Destination: {booking['destination']}"

    elif "places" in question or "itinerary" in question:
        return "Places: " + ", ".join(booking["places"])

    else:
        return "I can help with booking, budget, hotel, transport and itinerary."

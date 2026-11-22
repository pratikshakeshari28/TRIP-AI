import sqlite3
import uuid
import json

from pathlib import Path
from datetime import datetime

DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "trip_ai.db"
)


def create_booking(
    itinerary,
    hotel_name="Not Selected",
    transport_name="Not Selected",
    total_budget=0
):
    if itinerary.empty:
        return {"error": "No itinerary available."}

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    booking_id = "TRIP-" + uuid.uuid4().hex[:8].upper()

    destination = ", ".join(
        itinerary["City"].dropna().unique()
    )

    places = itinerary["Destination"].tolist()

    booking = {
        "booking_id": booking_id,
        "booking_date": datetime.now().isoformat(),
        "destination": destination,
        "hotel": hotel_name,
        "transport": transport_name,
        "places": json.dumps(places),
        "estimated_budget": float(total_budget),
        "status": "Demo Confirmed"
    }

    with sqlite3.connect(DB_PATH) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id TEXT PRIMARY KEY,
                booking_date TEXT,
                destination TEXT,
                hotel TEXT,
                transport TEXT,
                places TEXT,
                estimated_budget REAL,
                status TEXT
            )
        """)

        conn.execute("""
            INSERT INTO bookings VALUES (
                :booking_id,
                :booking_date,
                :destination,
                :hotel,
                :transport,
                :places,
                :estimated_budget,
                :status
            )
        """, booking)

    return booking


def get_booking(booking_id):

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        result = conn.execute(
            "SELECT * FROM bookings WHERE booking_id = ?",
            (booking_id,)
        ).fetchone()

    if result is None:
        return None

    booking = dict(result)
    booking["places"] = json.loads(booking["places"])

    return booking
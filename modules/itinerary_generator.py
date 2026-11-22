
import pandas as pd
from datetime import timedelta

TIME_ORDER = {"morning": 0, "all": 1, "anytime": 1, "afternoon": 2, "evening": 3, "night": 4}

COLUMNS = [
    "Day", "Date", "Destination", "City", "Type", "Best Time",
    "Visiting Hours", "Entrance Fee", "Rating", "Weekly Off",
]


def time_rank(value):
    return TIME_ORDER.get(str(value).strip().lower(), 1)


def interest_bonus(place_type, interests):
    place_type = str(place_type).lower()
    return 1.0 if any(i.lower() in place_type for i in (interests or [])) else 0.0


def is_closed(weekly_off, weekday):
    return bool(weekday) and str(weekly_off).strip().lower() == weekday.lower()


def sort_itinerary(itinerary):
    if itinerary.empty:
        return itinerary
    out = itinerary.copy()
    out["_day"] = out["Day"].str.extract(r"(\d+)").astype(int)
    out["_rank"] = out["Best Time"].map(time_rank)
    out = out.sort_values(["_day", "_rank"], kind="stable")
    return out.drop(columns=["_day", "_rank"]).reset_index(drop=True)


def generate_itinerary(df, city, days=2, daily_hours=6, interests=None, start_date=None):
    places = df[
        df["City"].str.contains(city, case=False, na=False, regex=False)
    ].copy()

    places = places[
        places["time needed to visit in hrs"].notna()
        & (places["time needed to visit in hrs"] > 0)
    ]

    if places.empty:
        return pd.DataFrame()

    places["score"] = places["Google review rating"].fillna(0) + places["Type"].map(
        lambda t: interest_bonus(t, interests)
    )
    places = places.sort_values("score", ascending=False)

    used = set()
    rows = []

    for day in range(1, days + 1):
        day_date = start_date + timedelta(days=day - 1) if start_date else None
        weekday = day_date.strftime("%A") if day_date else None
        hours_used = 0.0

        for index, place in places.iterrows():
            if index in used:
                continue
            if is_closed(place.get("Weekly Off", ""), weekday):
                continue

            visit_hours = float(place["time needed to visit in hrs"])

            if hours_used + visit_hours <= daily_hours:
                used.add(index)
                hours_used += visit_hours
                rows.append({
                    "Day": f"Day {day}",
                    "Date": day_date.strftime("%a %d %b") if day_date else "",
                    "Destination": place["Name"],
                    "City": place["City"],
                    "Type": place["Type"],
                    "Best Time": place.get("Best Time to visit", "All"),
                    "Visiting Hours": visit_hours,
                    "Entrance Fee": float(place["Entrance Fee in INR"]),
                    "Rating": place["Google review rating"],
                    "Weekly Off": place.get("Weekly Off", "Unknown"),
                })

    if not rows:
        return pd.DataFrame()

    return sort_itinerary(pd.DataFrame(rows, columns=COLUMNS))

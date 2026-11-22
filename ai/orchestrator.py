import math
from datetime import timedelta

import pandas as pd

from ai.llm_client import LLMError, generate_response
from ai.prompts import ITINERARY_PROMPT, SYSTEM_PROMPT

from modules.discovery_engine import recommend_places
from modules.itinerary_generator import (
    generate_itinerary,
    interest_bonus,
    is_closed,
    sort_itinerary,
)
from modules.preference_processor import process_preferences
from modules.validation_engine import validate_itinerary

TIERS = {
    "Smart Explorer": {
        "hotel": 1200, "transport": 400, "food": 400,
        "desc": "Budget stays, shared rides, local food",
    },
    "Balanced": {
        "hotel": 2500, "transport": 700, "food": 700,
        "desc": "3 to 4 star hotels, private cab",
    },
    "Boutique Luxury": {
        "hotel": 5000, "transport": 1200, "food": 1200,
        "desc": "Heritage stays, chauffeur, fine dining",
    },
    "Ultra Luxury": {
        "hotel": 12000, "transport": 3000, "food": 2500,
        "desc": "5 star palaces, private chauffeur",
    },
}
DEFAULT_TIER = "Balanced"


def _notify(on_step, label):
    if on_step:
        on_step(label)


def _recommend(df_city, interests, budget):
    if not interests:
        return recommend_places(df=df_city, budget=budget, top_n=10)

    frames = [
        recommend_places(df=df_city, preference=interest, budget=budget, top_n=10)
        for interest in interests
    ]
    combined = pd.concat(frames).drop_duplicates(subset="Name")
    return combined.sort_values("Google review rating", ascending=False).head(10)


def estimate_costs(itinerary, people, rates):
    days = itinerary["Day"].nunique()
    nights = max(0, days - 1)
    rooms = math.ceil(people / 2)

    sightseeing = float(itinerary["Entrance Fee"].sum()) * people
    hotel = float(nights * rates["hotel"] * rooms)
    transport = float(days * rates["transport"])
    food = float(days * rates["food"] * people)

    return {
        "Sightseeing": sightseeing,
        "Hotel": hotel,
        "Transport": transport,
        "Food": food,
        "Total Estimated Budget": sightseeing + hotel + transport + food,
    }


def recalculate(prefs, itinerary, rates):
    budget = estimate_costs(itinerary, prefs["people"], rates)
    validation = validate_itinerary(
        itinerary=itinerary,
        total_budget=budget["Total Estimated Budget"],
        user_budget=prefs["budget"],
        max_daily_hours=prefs["daily_hours"],
    )
    return budget, validation


def _offline_summary(destination, days, people, budget, interests, trip_budget, validation):
    total = trip_budget["Total Estimated Budget"]
    focus = f", focused on {', '.join(interests)}" if interests else ""

    lines = [
        "### Trip overview",
        f"A {days}-day plan for **{destination}** for {people} traveller(s){focus}.",
        "",
        "### Budget and tips",
        f"Estimated cost is **₹{total:,.0f}** against your budget of **₹{budget:,.0f}**.",
    ]
    lines += [f"- {error}" for error in validation.get("errors", [])]
    lines += [
        "",
        "_AI commentary is unavailable right now, so this summary was built "
        "directly from your plan data._",
    ]
    return "\n".join(lines)


def run_travel_agent(user_input, df, on_step=None):
    """Plan a trip.

    Extra keys read from user_input (all optional):
        tier        - a key of TIERS (default "Balanced")
        start_date  - datetime.date of the first day, used to skip closed places

    on_step: optional callback receiving a short progress label.

    Always returns a dict with a "status" key: "needs_info", "no_results" or "ok".
    """

    _notify(on_step, "Understanding your preferences")
    preferences = process_preferences(user_input)

    destination = preferences["destination"]
    budget = preferences["budget"]
    days = preferences["days"]
    interests = preferences["interests"]
    people = preferences["people"]
    daily_hours = preferences["daily_hours"]

    tier = user_input.get("tier") or DEFAULT_TIER
    rates = TIERS.get(tier, TIERS[DEFAULT_TIER])
    start_date = user_input.get("start_date")

    if not destination:
        return {"status": "needs_info", "message": "Which destination would you like to visit?"}

    if budget is None:
        return {"status": "needs_info", "message": "What is your total trip budget?"}

    _notify(on_step, f"Finding places in {destination}")
    df_city = df[
        df["City"].str.contains(destination, case=False, na=False, regex=False)
    ]
    recommended_places = _recommend(df_city, interests, budget)

    _notify(on_step, "Building your day-wise itinerary")
    itinerary = generate_itinerary(
        df=df,
        city=destination,
        days=days,
        daily_hours=daily_hours,
        interests=interests,
        start_date=start_date,
    )

    if itinerary.empty:
        return {
            "status": "no_results",
            "preferences": preferences,
            "message": (
                f"We could not build an itinerary for {destination}. "
                "Try another destination or more sightseeing hours per day."
            ),
        }

    trip_budget, validation = recalculate(preferences, itinerary, rates)

    _notify(on_step, "Writing your trip briefing with Gemini")

    prompt = ITINERARY_PROMPT.format(
        destination=destination,
        budget=f"{budget:,.0f}",
        days=days,
        interests=", ".join(interests) if interests else "open to anything",
        people=people,
    )
    prompt += f"""

Travel style: {tier} ({rates['desc']}).
Costs cover the whole group. Hotel cost is per room, with 2 travellers per room.

Python-generated recommendations:
{recommended_places.to_string(index=False)}

Python-generated itinerary (places closed on their weekly-off day were skipped):
{itinerary.drop(columns=['Weekly Off']).to_string(index=False)}

Python-calculated budget (estimated, INR):
{trip_budget}

Validation:
{validation}

Explain these results to the traveller.
Do not invent prices or availability.
"""

    ai_error = None
    try:
        ai_response = generate_response(prompt, system_instruction=SYSTEM_PROMPT)
        ai_source = "gemini"
    except LLMError as error:
        ai_error = str(error)
        ai_source = "offline"
        ai_response = _offline_summary(
            destination, days, people, budget, interests, trip_budget, validation
        )

    return {
        "status": "ok",
        "preferences": preferences,
        "tier": tier,
        "rates": rates,
        "start_date": start_date,
        "recommendations": recommended_places,
        "itinerary": itinerary,
        "budget": trip_budget,
        "validation": validation,
        "ai_response": ai_response,
        "ai_source": ai_source,
        "ai_error": ai_error,
    }


def _day_number(day_label):
    return int(str(day_label).split()[-1])


def find_replacements(df, result, day, place, top=3):
    """Best places that could replace `place` on `day` without breaking the day's hours."""
    itinerary = result["itinerary"]
    prefs = result["preferences"]
    removed = itinerary[(itinerary["Day"] == day) & (itinerary["Destination"] == place)].iloc[0]

    used = set(itinerary["Destination"])
    candidates = df[
        df["City"].str.contains(removed["City"], case=False, na=False, regex=False)
        & ~df["Name"].isin(used)
    ].copy()
    candidates = candidates[
        candidates["time needed to visit in hrs"].notna()
        & (candidates["time needed to visit in hrs"] > 0)
    ]

    hours_left = (
        itinerary[itinerary["Day"] == day]["Visiting Hours"].sum() - removed["Visiting Hours"]
    )
    candidates = candidates[
        candidates["time needed to visit in hrs"] + hours_left <= prefs["daily_hours"] + 1e-9
    ]

    start_date = result.get("start_date")
    if start_date is not None:
        weekday = (start_date + timedelta(days=_day_number(day) - 1)).strftime("%A")
        candidates = candidates[
            ~candidates["Weekly Off"].map(lambda w: is_closed(w, weekday))
        ]

    if candidates.empty:
        return candidates

    candidates["score"] = (
        candidates["Google review rating"].fillna(0)
        + candidates["Type"].map(lambda t: interest_bonus(t, prefs["interests"]))
        - (candidates["time needed to visit in hrs"] - removed["Visiting Hours"]).abs() * 0.15
    )
    return candidates.sort_values("score", ascending=False).head(top)


def apply_replacement(result, day, place, candidate):
    """Return a new itinerary with `place` swapped for `candidate` (a dataset row)."""
    itinerary = result["itinerary"].copy()
    mask = (itinerary["Day"] == day) & (itinerary["Destination"] == place)
    index = itinerary[mask].index[0]

    itinerary.loc[index, "Destination"] = candidate["Name"]
    itinerary.loc[index, "Type"] = candidate["Type"]
    itinerary.loc[index, "Best Time"] = candidate.get("Best Time to visit", "All")
    itinerary.loc[index, "Visiting Hours"] = float(candidate["time needed to visit in hrs"])
    itinerary.loc[index, "Entrance Fee"] = float(candidate["Entrance Fee in INR"])
    itinerary.loc[index, "Rating"] = candidate["Google review rating"]
    itinerary.loc[index, "Weekly Off"] = candidate.get("Weekly Off", "Unknown")
    return sort_itinerary(itinerary)


def remove_stop(result, day, place):
    """Return a new itinerary without `place` on `day`."""
    itinerary = result["itinerary"]
    keep = ~((itinerary["Day"] == day) & (itinerary["Destination"] == place))
    return itinerary[keep].reset_index(drop=True)

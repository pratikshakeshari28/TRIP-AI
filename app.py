import html
import json
import math
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
 
import pandas as pd
import streamlit as st
 
from ai.chat_agent import LLMError, consultant_reply, copilot_reply
from ai.llm_client import is_configured
from ai.orchestrator import (
    DEFAULT_TIER,
    TIERS,
    apply_replacement,
    find_replacements,
    recalculate,
    remove_stop,
    run_travel_agent,
)
from theme import CSS
from utils.photos import get_photos
 
try:
    from modules.booking_manager import DB_PATH, create_booking
    from modules.trip_support import answer_trip_query
 
    BOOKING_AVAILABLE = True
except Exception:  
    BOOKING_AVAILABLE = False
 
st.set_page_config(
    page_title="Trip AI - Smart Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
 
BASE_DIR = Path(__file__).resolve().parent
 
 
def find_data_file():
    wanted = BASE_DIR / "data" / "indian_destinations_clean.csv"
    if wanted.exists():
        return wanted
    for folder in (BASE_DIR / "data", BASE_DIR):
        found = sorted(folder.glob("*.csv")) if folder.exists() else []
        if found:
            return found[0]
    return wanted  
 
 
DATA_PATH = find_data_file()
 
S1, S2, S3 = "1. Inspiration & planning", "2. Itinerary", "3. Trip copilot & support"
STAGES = [S1, S2, S3]
KINDS = ["All items", "Stays", "Transfers", "Activities", "Dining"]
KIND_MAP = {"Stays": "Stay", "Transfers": "Transfer", "Activities": "Activity", "Dining": "Dining"}
 
WELCOME = (
    "Hi, I’m your TripAI consultant. Tell me where you want to go, your budget, "
    "how many days you have and what you enjoy. I’ll fill in your trip canvas as we talk."
)
 
 
# ---------- small helpers ----------
 
def h(markup):
    return "".join(line.strip() for line in markup.splitlines())
 
 
def money(value):
    return f"₹{value:,.0f}"
 
 
def hrs(value):
    return f"{value:g} hr"
 
 
def clock(hours_from_midnight):
    minutes = int(round(hours_from_midnight * 60))
    hour, minute = divmod(minutes, 60)
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"
 
 
def esc(value):
    return html.escape(str(value))
 
 
def photo_style(url):
    if not url:
        return ""
    safe = html.escape(url.replace("'", "%27"), quote=True)
    return (
        "background-image:linear-gradient(180deg,rgba(7,11,20,0) 40%,rgba(7,11,20,.8) 100%),"
        f"url('{safe}');"
    )
 
 
def thumb_style(url):
    if not url:
        return ""
    safe = html.escape(url.replace("'", "%27"), quote=True)
    return f"background-image:url('{safe}');"
 
 
@st.cache_data(show_spinner=False)
def load_data(path):
    frame = pd.read_csv(path)
 
    for column in ("Name", "City", "State", "Type"):
        frame[column] = frame[column].str.strip()
 
    frame["City"] = frame["City"].replace(
        {"dalhousie": "Dalhousie", "Bangalore": "Bengaluru", "New Delhi": "Delhi"}
    )
    frame["State"] = frame["State"].replace({"Maharastra": "Maharashtra"})
 
    for column in ("Entrance Fee in INR", "time needed to visit in hrs", "Google review rating"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["Entrance Fee in INR"] = frame["Entrance Fee in INR"].fillna(0)
 
    return frame.drop_duplicates(subset=["City", "Name"], keep="first").reset_index(drop=True)
 
 
@st.cache_data(show_spinner=False)
def city_table(frame):
    grouped = frame.groupby("City").agg(
        n=("Name", "count"),
        rating=("Google review rating", "mean"),
        fee=("Entrance Fee in INR", "mean"),
    )
    top = (
        frame.sort_values("Google review rating", ascending=False)
        .groupby("City")["Name"]
        .apply(lambda names: list(names.head(3)))
    )
    state = frame.groupby("City")["State"].agg(
        lambda s: s.mode().iat[0] if not s.mode().empty else ""
    )
    return grouped.join(top.rename("top")).join(state.rename("state")).reset_index()
 
 
def recommend_cities(frame, canvas, top=4):
    table = city_table(frame)
    table = table[table["n"] >= 3].copy()
 
    interests = [i.lower() for i in canvas["interests"]]
    if interests:
        matches = frame["Type"].astype(str).str.lower().apply(
            lambda t: any(i in t for i in interests)
        )
        share = frame[matches].groupby("City").size().div(frame.groupby("City").size())
        table["frac"] = table["City"].map(share).fillna(0.0)
    else:
        table["frac"] = 0.5
 
    tier = TIERS[canvas["tier"]]
    rooms = math.ceil(canvas["people"] / 2)
    table["per_day"] = (
        tier["hotel"] * rooms
        + tier["transport"]
        + tier["food"] * canvas["people"]
        + table["fee"].fillna(0) * canvas["people"] * 2
    )
 
    rating_part = ((table["rating"].fillna(0) - 3.8) / 1.0).clip(0, 1)
    table["score"] = (
        0.45 * table["frac"] + 0.35 * rating_part + 0.20 * (table["n"].clip(upper=12) / 12)
    )
    too_pricey = table["per_day"] * canvas["days"] > canvas["budget"]
    table.loc[too_pricey, "score"] = table.loc[too_pricey, "score"] * 0.6
 
    records = []
    for _, row in table.sort_values("score", ascending=False).head(top).iterrows():
        names = ", ".join(row["top"])
        records.append({
            "City": row["City"],
            "match": int(max(55, min(99, 60 + 39 * row["score"]))),
            "per_day": float(row["per_day"]),
            "blurb": f"{int(row['n'])} places to explore, including {names}.",
        })
    return records
 

 
def init_state(cities):
    ss = st.session_state
    default_city = "Goa" if "Goa" in cities else cities[0]
    ss.setdefault("canvas", {
        "dest": default_city, "budget": 25000, "days": 3, "people": 2, "hours": 6,
        "tier": DEFAULT_TIER, "start": date.today() + timedelta(days=14), "interests": [],
    })
    ss.setdefault("result", None)
    ss.setdefault("booking", None)
    ss.setdefault("disruption", None)
    ss.setdefault("chat", [{"role": "assistant", "content": WELCOME}])
    ss.setdefault("copilot", [])
    ss.setdefault("nav", S1)
 
    if ss.get("pending"):
        ss.canvas.update(ss.pop("pending"))
    if ss.get("goto"):
        ss.nav = ss.pop("goto")
 

 
def make_booking(result):
    total = result["budget"]["Total Estimated Budget"]
    rates = result["rates"]
    hotel = f"{result['tier']} stay (estimated {money(rates['hotel'])} per room per night)"
    transport = f"Private cab (estimated {money(rates['transport'])} per day)"
 
    if BOOKING_AVAILABLE:
        try:
            booking = create_booking(
                result["itinerary"], hotel_name=hotel, transport_name=transport, total_budget=total
            )
            if "error" not in booking:
                return booking
        except Exception:
            pass
 
    return {  
        "booking_id": "TRIP-" + uuid.uuid4().hex[:8].upper(),
        "booking_date": datetime.now().isoformat(),
        "destination": result["preferences"]["destination"],
        "hotel": hotel,
        "transport": transport,
        "places": result["itinerary"]["Destination"].tolist(),
        "estimated_budget": float(total),
        "status": "Demo Confirmed (not saved)",
    }
 
 
def list_bookings(limit=5):
    if not BOOKING_AVAILABLE:
        return []
    try:
        if not DB_PATH.exists():
            return []
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM bookings ORDER BY booking_date DESC LIMIT ?", (limit,)
            ).fetchall()
        bookings = []
        for row in rows:
            booking = dict(row)
            booking["places"] = json.loads(booking["places"])
            bookings.append(booking)
        return bookings
    except Exception:
        return []
 
 
def authorize_booking(result):
    ss = st.session_state
    ss.booking = make_booking(result)
    ss.result_booking_id = ss.booking["booking_id"]
    ss.copilot = []
    ss.disruption = None
    ss.goto = S3
    st.rerun()
 
 
 
def copilot_context():
    ss = st.session_state
    saved = ss.booking
    if saved and "error" not in saved and saved["booking_id"] != ss.get("result_booking_id"):
        return "\n".join([
            f"Booking ID: {saved['booking_id']}",
            f"Booking status: {saved['status']}",
            f"Destination: {saved['destination']}",
            f"Places: {', '.join(saved['places'])}",
            f"Hotel: {saved['hotel']}",
            f"Transport: {saved['transport']}",
            f"Estimated budget (INR): {saved['estimated_budget']:,.0f}",
            "This is a saved booking. The day-by-day plan is not stored with it.",
        ])
 
    result = ss.result
    if not result or result.get("status") != "ok":
        return "No trip has been planned yet."
 
    prefs = result["preferences"]
    lines = [
        f"Destination: {prefs['destination']}",
        f"Days: {prefs['days']}, travellers: {prefs['people']}, budget: INR {prefs['budget']:,.0f}",
        f"Travel style: {result['tier']}",
    ]
    booking = ss.booking
    if booking and "error" not in booking:
        lines += [f"Booking ID: {booking['booking_id']}", f"Booking status: {booking['status']}"]
    else:
        lines.append("Not booked yet.")
    lines += [
        "Itinerary:",
        result["itinerary"].drop(columns=["Weekly Off"]).to_string(index=False),
        f"Estimated budget (INR): {result['budget']}",
        f"Validation: {result['validation']}",
    ]
    return "\n".join(lines)
 
 
def run_copilot(question):
    ss = st.session_state
    history = list(ss.copilot)
    ss.copilot.append({"role": "user", "content": question})
 
    has_plan = bool(ss.result) and ss.result.get("status") == "ok"
    has_booking = bool(ss.booking) and "error" not in ss.booking
    if not (has_plan or has_booking):
        ss.copilot.append({"role": "assistant", "content": "Plan a trip in stage 1 first, then I can help with it."})
        st.rerun()
 
    try:
        with st.spinner("Copilot is checking your trip..."):
            answer = copilot_reply(question, copilot_context(), history)
    except LLMError:
        booking = ss.booking
        if booking and BOOKING_AVAILABLE:
            answer = answer_trip_query(question, booking["booking_id"])
        else:
            answer = "I could not reach Gemini right now. Please try again in a moment."
 
    ss.copilot.append({"role": "assistant", "content": answer})
    st.rerun()
 
 
 
def build_items(result, day):
    """Stays, transfers, activities and dining for one day. Costs are for the whole group."""
    itinerary = result["itinerary"]
    prefs = result["preferences"]
    rates = result["rates"]
    people = prefs["people"]
    rooms = math.ceil(people / 2)
 
    days = list(dict.fromkeys(itinerary["Day"]))
    is_last = day == days[-1]
    night_number = days.index(day) + 1
 
    items = [{
        "kind": "Transfer", "icon": "🚕", "title": "Private cab for the day",
        "sub": f"Local transfers between stops ({result['tier']})",
        "cost": float(rates["transport"]), "note": "Estimated", "badge": "Estimated",
    }]
 
    cursor = 9.0
    for _, row in itinerary[itinerary["Day"] == day].iterrows():
        start, cursor = cursor, cursor + float(row["Visiting Hours"])
        fee = float(row["Entrance Fee"])
        items.append({
            "kind": "Activity", "icon": "📍", "title": row["Destination"],
            "sub": f"{clock(start)} to {clock(cursor)}, {row['Type']}, rated {row['Rating']:.1f}",
            "cost": fee * people,
            "note": "Free entry" if fee == 0 else f"{money(fee)} x {people}",
            "badge": f"Best: {row['Best Time']}",
            "photo_q": f"{row['Destination']} {row['City']}",
        })
 
    items.append({
        "kind": "Dining", "icon": "🍽", "title": "Meals for the day",
        "sub": "Breakfast, lunch and dinner at local restaurants",
        "cost": float(rates["food"] * people),
        "note": f"{money(rates['food'])} x {people}", "badge": "Estimated",
    })
 
    if not is_last:
        items.append({
            "kind": "Stay", "icon": "🏨", "title": f"{result['tier']} stay, night {night_number}",
            "sub": f"{rooms} {'room' if rooms == 1 else 'rooms'} for {people} {'traveller' if people == 1 else 'travellers'}",
            "cost": float(rates["hotel"] * rooms),
            "note": f"{money(rates['hotel'])} x {rooms}", "badge": "Estimated",
        })
    return items
 
 
def item_html(item, photos):
    if item["kind"] == "Activity":
        style = thumb_style(photos.get(item.get("photo_q")))
        left = f'<div class="thumb" style="{style}"></div>'
    else:
        left = f'<div class="ico">{item["icon"]}</div>'
    return h(f"""
    <div class="item">{left}
      <div class="body">
        <div class="t">{esc(item['title'])}<span class="badge">{esc(item['badge'])}</span></div>
        <div class="s">{esc(item['sub'])}</div>
      </div>
      <div class="cost">{money(item['cost'])}<span>{esc(item['note'])}</span></div>
    </div>
    """)
 
 
def budget_html(budget, user_budget):
    total = budget["Total Estimated Budget"] or 1
    colors = {"Sightseeing": "#FFC21A", "Hotel": "#60A5FA", "Transport": "#34D399", "Food": "#F472B6"}
    rows = []
    for name, value in budget.items():
        if name == "Total Estimated Budget":
            continue
        share = value / total * 100
        rows.append(f"""
        <div class="bar-row">
          <div class="bar-top"><span>{name}</span><span>{money(value)} ({share:.0f}%)</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:{share:.1f}%;background:{colors[name]}"></div></div>
        </div>
        """)
    used = min(total / user_budget * 100, 100) if user_budget else 100
    over = total > user_budget
    note = f"Over budget by {money(total - user_budget)}" if over else f"{money(user_budget - total)} left to spend"
    rows.append(f"""
    <div class="bar-row" style="margin-top:20px">
      <div class="bar-top"><span><b>Total against your budget</b></span><span>{money(total)} of {money(user_budget)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:{used:.1f}%;background:{'#F87171' if over else '#34D399'}"></div></div>
      <div class="gauge-note">{note}</div>
    </div>
    """)
    return h("".join(rows))
 

 
def handle_consultant(question, cities, types):
    ss = st.session_state
    history = list(ss.chat)
    ss.chat.append({"role": "user", "content": question})
 
    try:
        with st.spinner("TripAI is thinking..."):
            reply, updates = consultant_reply(question, history, ss.canvas, cities, types, list(TIERS))
    except LLMError:
        reply = "I could not reach Gemini just now. You can still set your trip on the canvas on the right."
        updates = {}
 
    if updates:
        names = {"dest": "destination", "budget": "budget", "days": "days", "people": "travellers",
                 "hours": "hours per day", "tier": "style", "interests": "interests"}
        parts = []
        for key, value in updates.items():
            shown = ", ".join(value) if isinstance(value, list) else value
            parts.append(f"{names[key]}: {shown}")
        reply += "\n\n*Canvas updated: " + "; ".join(parts) + "*"
        ss.pending = updates
 
    ss.chat.append({"role": "assistant", "content": reply})
    st.rerun()
 
 
def generate_trip():
    ss = st.session_state
    c = ss.canvas
    user_input = {
        "destination": c["dest"], "budget": c["budget"], "days": c["days"],
        "people": c["people"], "daily_hours": c["hours"], "interests": c["interests"],
        "tier": c["tier"], "start_date": c["start"],
    }
    try:
        with st.status("Planning your trip", expanded=True) as status:
 
            def on_step(label):
                status.update(label=label)
                st.write(f"Done: {label}")
 
            result = run_travel_agent(user_input, df, on_step=on_step)
            status.update(label="Your trip is ready", state="complete", expanded=False)
    except Exception as error:
        st.error(f"The trip could not be planned: {error}")
        return
 
    ss.result = result
    ss.booking = None
    ss.disruption = None
    ss.copilot = []
    if result["status"] == "ok":
        ss.goto = S2
        st.rerun()
    else:
        st.warning(result["message"])
 
 
def stage_inspiration(cities, city_counts, interest_options):
    ss = st.session_state
    c = ss.canvas
 
    st.markdown(h("""
    <div class="eyebrow">STAGE 01 / INSPIRATION &amp; CONVERSATIONAL PLANNING</div>
    <div class="h1">Where would you like to escape next?</div>
    <div class="lead">Chat with TripAI to refine your travel vision, or pick a destination below.
    Your live trip canvas updates with every choice.</div>
    """), unsafe_allow_html=True)
 
    left, right = st.columns([2.1, 1], gap="large")
 
    with left:
        records = recommend_cities(df, c)
        photos = get_photos([f"{r['City']} India" for r in records])
 
        with st.container(border=True):
            st.markdown(
                '<div class="panel-head"><div>Recommended destinations for your profile</div>'
                "<span>Click a destination to update the canvas</span></div>",
                unsafe_allow_html=True,
            )
            columns = st.columns(len(records)) if records else []
            for column, rec in zip(columns, records):
                selected = rec["City"] == c["dest"]
                with column:
                    st.markdown(h(f"""
                    <div class="dest {'sel' if selected else ''}">
                      <div class="dest-ph" style="{photo_style(photos.get(rec['City'] + ' India'))}">
                        <span class="match">{rec['match']}% match</span>
                        <div class="dest-name">{esc(rec['City'])}</div>
                      </div>
                      <div class="dest-body">
                        <div class="dest-desc">{esc(rec['blurb'])}</div>
                        <div class="dest-foot">{money(rec['per_day'])}/day</div>
                      </div>
                    </div>
                    """), unsafe_allow_html=True)
                    if st.button(
                        "Selected" if selected else "Select",
                        key=f"pick_{rec['City']}",
                        type="primary" if selected else "secondary",
                    ):
                        ss.pending = {"dest": rec["City"]}
                        st.rerun()
 
        with st.container(border=True):
            st.markdown(
                '<div class="panel-head"><div><span class="live"></span>TripAI trip consultant</div>'
                "<span>Powered by Gemini</span></div>",
                unsafe_allow_html=True,
            )
            box = st.container(height=300)
            with box:
                for message in ss.chat:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
 
            chips = [
                "Beach holiday in Goa for 4 days",
                "Heritage trip in Delhi under ₹20,000",
                "Weekend in Hyderabad with family",
            ]
            for column, text in zip(st.columns(3), chips):
                if column.button(text, key=f"chip_{text}"):
                    ss.queued = text
 
            typed = st.chat_input(
                "Tell me where you want to go, your budget and what you enjoy",
                key="consultant_input",
            )
            question = ss.pop("queued", None) or typed
            if question:
                handle_consultant(question, cities, interest_options)
 
    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="panel-head"><div><span class="live"></span>Live trip canvas</div>'
                "<span>Real-time sync</span></div>",
                unsafe_allow_html=True,
            )
            hero = st.empty()
 
            c["dest"] = st.selectbox(
                "Destination", cities, index=cities.index(c["dest"]),
                format_func=lambda city: f"{city} ({city_counts[city]} places)",
            )
            col_a, col_b = st.columns(2)
            c["start"] = col_a.date_input(
                "Depart", value=max(c["start"], date.today()), min_value=date.today()
            )
            c["days"] = int(col_b.number_input("Days", min_value=1, max_value=14, value=int(c["days"])))
            end = c["start"] + timedelta(days=c["days"] - 1)
            st.caption(f"Return {end:%a %d %b %Y}, {c['days']} days and {c['days'] - 1} nights")
 
            col_c, col_d = st.columns(2)
            c["people"] = int(col_c.number_input("Travellers", min_value=1, max_value=20, value=int(c["people"])))
            c["budget"] = int(col_d.number_input(
                "Budget (₹)", min_value=1000, max_value=10_000_000, value=int(c["budget"]), step=1000
            ))
            c["hours"] = st.slider("Sightseeing hours per day", 2, 12, int(c["hours"]))
            c["tier"] = st.selectbox("Travel style", list(TIERS), index=list(TIERS).index(c["tier"]))
            st.caption(TIERS[c["tier"]]["desc"])
            c["interests"] = st.multiselect(
                "Interests (optional)", interest_options,
                default=[i for i in c["interests"] if i in interest_options],
                placeholder="For example: Temple, Fort, Beach",
            )
 
            state = df.loc[df["City"] == c["dest"], "State"]
            photo = get_photos([f"{c['dest']} India"]).get(f"{c['dest']} India")
            hero.markdown(h(f"""
            <div class="canvas-ph" style="{photo_style(photo)}">
              <div class="canvas-txt">
                <div class="canvas-name">{esc(c['dest'])}</div>
                <div class="canvas-sub">{esc(state.iloc[0] if len(state) else '')}, {city_counts[c['dest']]} places</div>
              </div>
            </div>
            """), unsafe_allow_html=True)
 
            if st.button("Build my itinerary", type="primary", key="build"):
                generate_trip()
 
 
def stage_itinerary():
    ss = st.session_state
    result = ss.result
 
    if not result:
        st.markdown(
            '<div class="empty"><b>No itinerary yet</b>Set up your trip in stage 1 and select Build my itinerary.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Go to planning", key="to_s1"):
            ss.goto = S1
            st.rerun()
        return
    if result["status"] != "ok":
        st.warning(result["message"])
        return
 
    prefs = result["preferences"]
    itinerary = result["itinerary"]
    budget = result["budget"]
    validation = result["validation"]
    total = budget["Total Estimated Budget"]
    remaining = prefs["budget"] - total
    planned_days = itinerary["Day"].nunique()
 
    top, back, book = st.columns([3, 1.1, 1.8])
    top.markdown(h(f"""
    <div class="eyebrow">STAGE 02 / DYNAMIC ITINERARY</div>
    <div class="h1">{esc(prefs['destination'])} curated itinerary</div>
    <div class="lead">{planned_days} days for {prefs['people']} {'traveller' if prefs['people'] == 1 else 'travellers'},
    {esc(result['tier'])} style. Stops are chosen by rating and your interests, and places closed on
    their weekly-off day are skipped.</div>
    """), unsafe_allow_html=True)
    if back.button("Modify preferences", key="modify"):
        ss.goto = S1
        st.rerun()
    if book.button(f"Authorize booking ({money(total)})", type="primary", key="authorize"):
        authorize_booking(result)
 
    st.markdown(h(f"""
    <div class="strip">
      <div class="cell"><div class="label">Total estimated cost</div><div class="value">{money(total)}</div>
        <div class="sub">for all travellers</div></div>
      <div class="cell"><div class="label">Target budget limit</div><div class="value">{money(prefs['budget'])}</div>
        <div class="sub">your budget</div></div>
      <div class="cell"><div class="label">Budget variance</div>
        <div class="value {'good' if remaining >= 0 else 'bad'}">{'+' if remaining >= 0 else '-'}{money(abs(remaining))} {'under' if remaining >= 0 else 'over'}</div>
        <div class="sub">{'within budget' if remaining >= 0 else 'reduce days or change style'}</div></div>
      <div class="cell"><div class="label">Stops planned</div><div class="value">{len(itinerary)}</div>
        <div class="sub">{hrs(itinerary['Visiting Hours'].sum())} of sightseeing</div></div>
    </div>
    """), unsafe_allow_html=True)
 
    days = list(dict.fromkeys(itinerary["Day"]))
    dates = dict(zip(itinerary["Day"], itinerary["Date"]))
    if ss.get("day_sel") not in days:
        ss.pop("day_sel", None)
    day = st.radio(
        "Day", days, horizontal=True, key="day_sel", label_visibility="collapsed",
        format_func=lambda d: f"{d}  {dates.get(d, '')}".strip(),
    )
 
    names = itinerary.loc[itinerary["Day"] == day, "Destination"].tolist()
    head, filt = st.columns([2, 2])
    head.markdown(h(f"""
    <div class="dayhead"><div class="t">{esc(day)}: {esc(names[0])}{' and more' if len(names) > 1 else ''}</div>
    <div class="s">{esc(', '.join(names))}</div></div>
    """), unsafe_allow_html=True)
    kind = filt.radio("Filter", KINDS, horizontal=True, key="kind_sel", label_visibility="collapsed")
 
    items = build_items(result, day)
    if kind != "All items":
        items = [i for i in items if i["kind"] == KIND_MAP[kind]]
    photos = get_photos([i["photo_q"] for i in items if i.get("photo_q")])
    st.markdown("".join(item_html(i, photos) for i in items), unsafe_allow_html=True)
 
    col_budget, col_ai = st.columns(2, gap="large")
    with col_budget:
        with st.container(border=True):
            st.markdown('<div class="panel-head"><div>Budget breakdown</div><span>Estimated, not live prices</span></div>',
                        unsafe_allow_html=True)
            st.markdown(budget_html(budget, prefs["budget"]), unsafe_allow_html=True)
            nights = max(0, planned_days - 1)
            st.caption(
                f"Hotel {money(result['rates']['hotel'])} per room for {nights} night(s), "
                f"transport {money(result['rates']['transport'])} per day, "
                f"food {money(result['rates']['food'])} per person per day."
            )
    with col_ai:
        with st.container(border=True):
            label = "Written by Gemini" if result["ai_source"] == "gemini" else "Offline summary, Gemini not reachable"
            st.markdown(
                f'<div class="panel-head"><div>AI trip briefing</div>'
                f'<span class="pill {"ok" if result["ai_source"] == "gemini" else "warn"}">{label}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(result["ai_response"])
            if result.get("ai_error"):
                with st.expander("Why is the AI summary offline?"):
                    st.code(result["ai_error"])
            if validation["valid"]:
                st.success("All plan checks passed.")
            else:
                for error in validation["errors"]:
                    st.warning(error)
            if planned_days < prefs["days"]:
                st.info(f"Only {planned_days} of {prefs['days']} days could be filled with the places available.")
 
    st.download_button(
        "Download itinerary (CSV)",
        data=itinerary.to_csv(index=False).encode("utf-8"),
        file_name=f"trip_{prefs['destination'].lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
 
 
def render_disruption(result):
    ss = st.session_state
    d = ss.disruption
    if not d:
        return
 
    prefs = result["preferences"]
    people = prefs["people"]
    st.markdown(h(f"""
    <div class="alert">
      <div class="alert-top"><span class="mono">LIVE DISRUPTION DETECTED</span><span class="pill bad">High priority</span></div>
      <div class="alert-title">{esc(d['place'])} is unavailable</div>
      <div class="alert-text">{esc(d['day'])} {esc(d['date'])}: {esc(d['reason'].lower())}.</div>
      <div class="impact"><b>Impact assessment:</b> this frees {hrs(d['hours'])} in your day and removes
      {money(d['fee'] * people)} of entry fees.
      {len(d['options'])} replacement(s) fit the remaining time and weekly-off days.</div>
    </div>
    <div class="res-title">RECOMMENDED ONE-CLICK RESOLUTIONS</div>
    """), unsafe_allow_html=True)
 
    for i, option in enumerate(d["options"]):
        fee = float(option["Entrance Fee in INR"])
        label = (
            f"Swap in {option['Name']}  ({hrs(float(option['time needed to visit in hrs']))}, "
            f"{'free entry' if fee == 0 else money(fee)}, rated {option['Google review rating']:.1f})"
        )
        if st.button(label, key=f"swap_{i}"):
            new_itinerary = apply_replacement(result, d["day"], d["place"], option)
            budget, validation = recalculate(prefs, new_itinerary, result["rates"])
            result.update(itinerary=new_itinerary, budget=budget, validation=validation)
            ss.copilot.append({
                "role": "assistant",
                "content": f"Done. I swapped **{d['place']}** for **{option['Name']}** on {d['day']}. "
                           f"New estimated total: {money(budget['Total Estimated Budget'])}.",
            })
            ss.disruption = None
            st.rerun()
 
    if len(result["itinerary"]) <= 1:
        st.caption("This is the only stop in your trip, so it cannot be removed. Swap it instead.")
    elif st.button(f"Remove {d['place']} from the plan", key="remove_stop"):
        new_itinerary = remove_stop(result, d["day"], d["place"])
        budget, validation = recalculate(prefs, new_itinerary, result["rates"])
        result.update(itinerary=new_itinerary, budget=budget, validation=validation)
        ss.copilot.append({
            "role": "assistant",
            "content": f"I removed **{d['place']}** from {d['day']}. "
                       f"New estimated total: {money(budget['Total Estimated Budget'])}.",
        })
        ss.disruption = None
        st.rerun()
 
 
def stage_copilot():
    ss = st.session_state
    result = ss.result
    ok = bool(result) and result.get("status") == "ok"
 
    st.markdown(h("""
    <div class="eyebrow">STAGE 03 / TRIP MANAGEMENT &amp; POST-BOOKING COPILOT</div>
    <div class="h1">Active trips &amp; concierge support</div>
    <div class="lead">See your saved bookings, test what happens when a stop becomes unavailable,
    and ask the copilot anything about your plan.</div>
    """), unsafe_allow_html=True)
 
    left, right = st.columns([1.1, 1], gap="large")
 
    with left:
        bookings = list_bookings()
        current = ss.booking if ss.booking and "error" not in ss.booking else None
        if current and current["booking_id"] not in [b["booking_id"] for b in bookings]:
            bookings.insert(0, current)
 
        if not bookings:
            st.markdown(
                '<div class="empty"><b>No bookings yet</b>Build an itinerary and select Authorize booking in stage 2.</div>',
                unsafe_allow_html=True,
            )
        for booking in bookings:
            active = bool(current) and booking["booking_id"] == current["booking_id"]
            st.markdown(h(f"""
            <div class="bk {'active' if active else ''}">
              <div class="bk-top"><span class="mono">REF: {esc(booking['booking_id'])}</span>
                <span class="pill ok">{esc(booking['status'])}</span></div>
              <div class="bk-title">{esc(booking['destination'])}</div>
              <div class="bk-sub">{len(booking['places'])} {'place' if len(booking['places']) == 1 else 'places'}, estimated {money(booking['estimated_budget'])}</div>
            </div>
            """), unsafe_allow_html=True)
            if st.button(
                "Selected" if active else "Select this trip",
                key=f"bk_{booking['booking_id']}",
                type="primary" if active else "secondary",
            ) and not active:
                ss.booking = booking
                ss.copilot = []
                ss.disruption = None
                st.rerun()
 
        same_trip = (not current) or current["booking_id"] == ss.get("result_booking_id")
        if ok and not same_trip:
            st.info(
                "The disruption simulator needs the full day-by-day plan, which is only kept for the trip "
                "you planned in this session. Select that trip above, or plan a new one."
            )
        if ok and same_trip:
            itinerary = result["itinerary"]
            with st.container(border=True):
                st.markdown('<div class="panel-head"><div>Disruption simulator</div><span>Demo</span></div>',
                            unsafe_allow_html=True)
                stops = list(zip(itinerary["Day"], itinerary["Destination"]))
                pick = st.selectbox(
                    "Which stop is affected?", range(len(stops)),
                    format_func=lambda i: f"{stops[i][0]}: {stops[i][1]}",
                )
                reason = st.selectbox("What happened?", ["Closed unexpectedly", "Heavy rain forecast", "Very long queues"])
                if st.button("Simulate disruption", type="primary", key="simulate"):
                    day, place = stops[pick]
                    row = itinerary[(itinerary["Day"] == day) & (itinerary["Destination"] == place)].iloc[0]
                    options = find_replacements(df, result, day, place)
                    ss.disruption = {
                        "day": day, "date": row["Date"], "place": place, "reason": reason,
                        "hours": float(row["Visiting Hours"]), "fee": float(row["Entrance Fee"]),
                        "options": options.to_dict("records"),
                    }
            render_disruption(result)
 
    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="panel-head"><div><span class="live"></span>TripAI post-booking copilot</div>'
                "<span>24/7 guide</span></div>",
                unsafe_allow_html=True,
            )
            box = st.container(height=360)
            with box:
                if not ss.copilot:
                    with st.chat_message("assistant"):
                        st.markdown(
                            "Hello! I’m your TripAI copilot. Ask me about your itinerary, budget, "
                            "packing or how to save money."
                        )
                for message in ss.copilot:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
 
            chips = ["Summarise my plan", "What should I pack?", "How can I save money?"]
            for column, text in zip(st.columns(3), chips):
                if column.button(text, key=f"cchip_{text}"):
                    ss.cqueued = text
 
            typed = st.chat_input("Ask about your trip", key="copilot_input")
            question = ss.pop("cqueued", None) or typed
            if question:
                run_copilot(question)
 
 
st.markdown(CSS, unsafe_allow_html=True)
 
try:
    df = load_data(DATA_PATH)
except Exception as error:
    st.error(
        f"Could not load the destination data. Put the CSV file at {BASE_DIR / 'data' / 'indian_destinations_clean.csv'}. "
        f"Details: {error}"
    )
    st.stop()
 
city_counts = df["City"].value_counts()
cities = sorted(city_counts.index.tolist())
interest_options = df["Type"].dropna().value_counts().index.tolist()  # most common first
 
init_state(cities)

 
brand, nav, active, review = st.columns([1.15, 4.3, 2.3, 1.3])
brand.markdown(
    '<div class="brand"><span class="brand-ico">✈</span>Trip<b>AI</b></div>',
    unsafe_allow_html=True,
)
nav.radio("Stage", STAGES, horizontal=True, key="nav", label_visibility="collapsed")
current_result = st.session_state.result
if current_result and current_result.get("status") == "ok":
    p = current_result["preferences"]
    active.markdown(
        f'<div class="active-pill">Active: <b>{esc(p["destination"])} trip, {p["days"]} days</b></div>',
        unsafe_allow_html=True,
    )
if review.button("Review itinerary", type="primary", key="hdr_review"):
    st.session_state.goto = S2
    st.rerun()
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
 
stage = st.session_state.nav
if stage == S1:
    stage_inspiration(cities, city_counts, interest_options)
elif stage == S2:
    stage_itinerary()
else:
    stage_copilot()
 
st.caption(
    "Costs are estimates from simulated daily rates and dataset entry fees, not live prices. "
    "Bookings are demo records only. Photos come from Wikipedia."
)
if not is_configured():
    st.caption("No GEMINI_API_KEY found: chat and AI briefings will not work until you add it to .env.")
 

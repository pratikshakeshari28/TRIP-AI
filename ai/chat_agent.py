import json
import re
 
from ai.llm_client import LLMError, generate_response
 
CONSULTANT_SYSTEM = """
You are the planning consultant inside a travel app for India.
The traveller chats with you and the app fills a "trip canvas" from your answer.
 
Reply with JSON only, no other text, in exactly this shape:
{"reply": "<1 to 3 friendly sentences>",
 "updates": {"destination": null, "budget": null, "days": null, "people": null,
             "hours": null, "tier": null, "interests": null}}
 
Rules:
- Put a value in "updates" only when the traveller stated or clearly implied it.
- "destination" must be exactly one city from the available cities list.
- "interests" must be a list of items from the available interest types list.
- "tier" must be one of the available travel styles.
- "budget" is the total trip budget in INR as a number. "hours" is sightseeing hours per day.
- If a destination, budget or number of days is missing, ask for ONE of them in "reply".
- Never invent prices, availability or places outside the lists.
"""
 
COPILOT_SYSTEM = """
You are TripAI Copilot, a post-booking assistant for one traveller.
Answer using only the trip context you are given.
 
Rules:
- This is a demo booking. Never claim a real booking, payment, refund or live status.
- All costs are estimates. Never invent prices, opening hours or availability.
- Keep answers short, friendly and practical (under 120 words).
- To change the plan, tell the traveller to use the disruption simulator or go back to stage 1.
"""
 
 
def _extract_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
 
 
def _number(value, low, high):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None
 
 
def clean_updates(updates, cities, types, tiers):
    out = {}
    if not isinstance(updates, dict):
        return out
 
    dest = updates.get("destination")
    if isinstance(dest, str):
        match = next((c for c in cities if c.lower() == dest.strip().lower()), None)
        if match:
            out["dest"] = match
 
    budget = _number(updates.get("budget"), 1000, 10_000_000)
    if budget is not None:
        out["budget"] = int(budget)
 
    for key, field, low, high in (("days", "days", 1, 14), ("people", "people", 1, 20), ("hours", "hours", 2, 12)):
        value = _number(updates.get(key), low, high)
        if value is not None:
            out[field] = int(value)
 
    tier = updates.get("tier")
    if isinstance(tier, str):
        match = next((t for t in tiers if t.lower() == tier.strip().lower()), None)
        if match:
            out["tier"] = match
 
    interests = updates.get("interests")
    if isinstance(interests, list):
        lowered = {t.lower(): t for t in types}
        picked = [lowered[i.strip().lower()] for i in interests if isinstance(i, str) and i.strip().lower() in lowered]
        if picked:
            out["interests"] = picked
 
    return out
 
 
def _history_text(history, limit=8):
    lines = []
    for message in history[-limit:]:
        who = "Traveller" if message["role"] == "user" else "Assistant"
        lines.append(f"{who}: {message['content']}")
    return "\n".join(lines)
 
 
def consultant_reply(message, history, canvas, cities, types, tiers):
    snapshot = {
        "destination": canvas["dest"],
        "budget": canvas["budget"],
        "days": canvas["days"],
        "people": canvas["people"],
        "hours": canvas["hours"],
        "tier": canvas["tier"],
        "interests": canvas["interests"],
    }
    prompt = (
        f"Current trip canvas: {json.dumps(snapshot)}\n\n"
        f"Available cities: {', '.join(cities)}\n\n"
        f"Available interest types: {', '.join(types[:60])}\n\n"
        f"Available travel styles: {', '.join(tiers)}\n\n"
        f"Conversation so far:\n{_history_text(history)}\n\n"
        f"Traveller: {message}"
    )
    raw = generate_response(prompt, system_instruction=CONSULTANT_SYSTEM, temperature=0.3)
 
    data = _extract_json(raw)
    if not data:
        return raw.strip(), {}
 
    reply = str(data.get("reply") or "").strip() or "Done. I updated your trip canvas."
    return reply, clean_updates(data.get("updates"), cities, types, tiers)
 
 
def copilot_reply(question, context, history):
    prompt = (
        f"Trip context:\n{context}\n\n"
        f"Conversation so far:\n{_history_text(history, 6)}\n\n"
        f"Traveller: {question}"
    )
    return generate_response(prompt, system_instruction=COPILOT_SYSTEM, temperature=0.4)
 

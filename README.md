Trip AI

An AI travel planner for India. Tell it where you want to go, your budget and what you enjoy. It builds a day-wise itinerary with a cost estimate, explains the plan in plain language with Google Gemini, and helps when plans change.

Built with Python, Streamlit and the Gemini API.

Screenshots
Plan	Itinerary	Copilot
Planning	Itinerary	Copilot
What you can do

1. Plan

Browse recommended destinations with photos, a match score and an estimated cost per day.
Chat with a Gemini consultant. Try: "4 days in Goa for 2 people, beaches, under 30,000". The trip canvas fills itself in.
Set dates, travellers, budget, travel style (Smart Explorer to Ultra Luxury) and interests.

2. Get an itinerary

See the estimated total, your budget and how far under or over you are.
Browse each day by stays, transfers, activities and dining, with a photo for every place.
Stops are ranked by rating and your interests. Places closed on their weekly-off day are skipped.
If a city has too few places for your trip length, nearby cities in the same state fill the remaining days, with an estimated intercity cost.
Read an AI briefing, check the budget breakdown and download the plan as CSV.

3. Manage the trip

Save a demo booking with your name and phone number.
Test the disruption simulator: mark a stop as unavailable, then swap it for a suggested replacement or remove it. The budget updates instantly.
Ask the copilot questions about your trip.

An admin section lists every saved booking behind a password.

How it works
Traveller input
Preference processing
Itinerary and budget engine(Python)
Validation
Gemini briefing
Dashboard

The main design choice is a clear split of work:

Python decides the facts. Recommendations, the schedule, closed days, costs and budget checks all come from deterministic code and the dataset.
Gemini explains and chats. It receives the finished plan and writes the briefing, so it cannot invent prices or places. Chat replies are returned as JSON and validated before they change the trip canvas.
Everything degrades gracefully. Gemini calls have a timeout, retries and model fallback. If Gemini is down, the app shows a plain summary and keeps working. If photos cannot load, a gradient is shown instead.
Folder or file	Purpose
app.py, theme.py	Streamlit dashboard and dark theme
ai/orchestrator.py	Runs the plan, calculates costs, handles replanning
ai/chat_agent.py	Gemini consultant and copilot chat
ai/llm_client.py	Gemini client with timeout, retries and fallback
modules/	Recommendations, itinerary, validation and bookings
utils/photos.py	Destination photos from Wikipedia, cached on disk
data/	Dataset of tourist places in India
Run it locally

You need Python 3.10 or newer and a free Gemini API key from Google AI Studio.

pip install -r requirements.txt

Create a .env file (you can copy .env.example):

GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
ADMIN_PASSWORD=choose_a_password

Put the dataset at data/indian_destinations_clean.csv, then start the app:

streamlit run app.py
Good to know
Costs are estimates. Hotel, transport, food and intercity rates are simulated for each travel style. Entry fees come from the dataset. Nothing here is a live price.
Bookings are demo only. No payment is taken and nothing is sent to hotels or airlines.
Personal data. Names and phone numbers are stored in a local SQLite file (database/trip_ai.db), which is excluded from Git. Use fake details when you try the app.
Dataset limits. The dataset has a limited number of places per city, and some small cities have only one or two.
Photos come from Wikipedia and need internet access the first time.
Ideas for next steps
Real flight, hotel and train data through travel APIs
Travel time between places when scheduling a day
User accounts and a booking history page
A larger dataset with opening hours and coordinates
Deployment with a hosted database
Tech stack

Python, Streamlit, pandas, SQLite, Google Gemini API, Wikipedia API.

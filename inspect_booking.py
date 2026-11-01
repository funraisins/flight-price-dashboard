
import os
import requests
import json
from dotenv import load_dotenv
from datetime import date, timedelta
from flight_api import search_flights

load_dotenv()
API_KEY = os.getenv("SERPAPI_KEY")

test_date = (date.today() + timedelta(days=30)).isoformat()

# First, retrieve one flight offer
results = search_flights(
    origin="LGW",
    destination="MAD",
    departure_date=test_date
)

offers = (
    results.get("best_flights", [])
    + results.get("other_flights", [])
)

if not offers:
    print("No flight offers found.")
    raise SystemExit

# Find a flight with a booking token
offer = next(
    (item for item in offers if item.get("booking_token")),
    None
)

if offer is None:
    print("No booking token available.")
    raise SystemExit

booking_token = offer["booking_token"]

# Request booking information
params = {
    "engine": "google_flights",
    "departure_id": "LGW",
    "arrival_id": "MAD",
    "outbound_date": test_date,
    "type": "2",
    "booking_token": booking_token,
    "currency": "GBP",
    "hl": "en",
    "api_key": API_KEY
}

response = requests.get(
    "https://serpapi.com/search.json",
    params=params,
    timeout=30
)

data = response.json()

# Save the booking response locally for testing
with open("booking_response.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Booking response saved successfully!")

if response.status_code != 200 or "error" in data:
    print(
        "Booking request failed:",
        data.get("error", f"HTTP {response.status_code}")
    )
    raise SystemExit

print("TOP-LEVEL BOOKING RESPONSE KEYS:")
print(list(data.keys()))

print("\nBAGGAGE-RELATED INFORMATION:")

def find_baggage(data, path=""):
    if isinstance(data, dict):
        for key, value in data.items():
            current = f"{path}.{key}" if path else key

            if any(word in key.lower() for word in [
                "bag", "luggage", "carry_on", "checked"
            ]):
                print(current, ":", value)

            find_baggage(value, current)

    elif isinstance(data, list):
        for index, item in enumerate(data):
            find_baggage(item, f"{path}[{index}]")

find_baggage(data)


print("\nBOOKING OPTIONS SUMMARY")
print("-" * 60)

booking_options = data.get("booking_options", [])

for index, option in enumerate(booking_options):

    print(f"\nOPTION {index}")

    print("Top-level keys:", list(option.keys()))

    together = option.get("together", {})

    if isinstance(together, dict):
        print("Booking provider:", together.get("book_with"))
        print("Booking price:", together.get("price"))
        print("Baggage prices:", together.get("baggage_prices"))
        print("Together keys:", list(together.keys()))

    separate = option.get("separate_tickets")

    if separate:
        print("Separate tickets:", True)

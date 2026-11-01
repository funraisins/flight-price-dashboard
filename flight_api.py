import os
import requests
from dotenv import load_dotenv
from datetime import date, timedelta

# Load API credentials from .env
load_dotenv()

API_KEY = os.getenv("SERPAPI_KEY")

def search_flights(origin, destination, departure_date):
    """
    Search Google Flights through SerpApi.
    
    origin: London airport code, e.g. LHR
    destination: Madrid airport code, MAD
    departure_date: YYYY-MM-DD
    """

    if not API_KEY:
        raise ValueError("SERPAPI_KEY is missing from .env")

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "type": "2",
        "currency": "GBP",
        "hl": "en",
        "api_key": API_KEY
    }

    response = requests.get(url, params=params, timeout=30)

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"API returned a non-JSON response. "
            f"HTTP status: {response.status_code}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"SerpApi error ({response.status_code}): "
            f"{data.get('error', 'Unknown error')}"
        )

    if "error" in data:
        raise RuntimeError(data["error"])

    return data


def search_multiple_airports(
    origins,
    destination,
    departure_date
):
    """
    Search multiple departure airports and combine results.

    Each airport requires a separate API request.
    """

    all_offers = []
    errors = {}

    for origin in origins:
        print(f"Searching {origin} -> {destination}...")

        try:
            results = search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date
            )

            offers = (
                results.get("best_flights", [])
                + results.get("other_flights", [])
            )

            for offer in offers:
                offer_copy = offer.copy()
                offer_copy["searched_origin"] = origin
                all_offers.append(offer_copy)

            print(f"Found {len(offers)} offers")

        except Exception as e:
            errors[origin] = str(e)
            print(f"Search failed for {origin}: {type(e).__name__}")

    return all_offers, errors


def get_booking_details(
    origin,
    destination,
    departure_date,
    booking_token
):
    """
    Retrieve booking options for a selected flight.
    """

    if not API_KEY:
        raise ValueError("SERPAPI_KEY is missing")

    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
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

    # Avoid exposing API keys in HTTP error URLs
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"Booking API returned HTTP {response.status_code}"
        )

    if response.status_code != 200 or "error" in data:
        raise RuntimeError(
            data.get("error", f"HTTP {response.status_code}")
        )

    return data

# Run this test only when executing flight_api.py directly
if __name__ == "__main__":
    from datetime import date, timedelta

    test_date = (date.today() + timedelta(days=30)).isoformat()

    offers, errors = search_multiple_airports(
        origins=["LHR", "LGW"],
        destination="MAD",
        departure_date=test_date
    )

    print(f"\nTotal offers found: {len(offers)}")

    for offer in offers[:10]:
        print({
            "Airport": offer["searched_origin"],
            "Price": offer.get("price")
        })

    if errors:
        print("\nSearch errors:", errors)
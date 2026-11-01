
from flight_api import search_flights
from datetime import date, timedelta
import json

# Test one airport and one date
test_date = (date.today() + timedelta(days=30)).isoformat()

results = search_flights(
    origin="LGW",
    destination="MAD",
    departure_date=test_date
)

# Inspect the keys returned by SerpApi
print("\nTOP-LEVEL RESPONSE KEYS:")
print(list(results.keys()))

offers = (
    results.get("best_flights", [])
    + results.get("other_flights", [])
)

if offers:
    first_offer = offers[0]

    print("\nFIRST FLIGHT OFFER:")
    print(json.dumps(first_offer, indent=2))

    print("\nBAGGAGE-RELATED FIELDS:")

    def find_baggage_fields(data, path=""):
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if any(word in key.lower() for word in [
                    "baggage", "bag", "luggage"
                ]):
                    print(current_path, ":", value)

                find_baggage_fields(value, current_path)

        elif isinstance(data, list):
            for index, item in enumerate(data):
                find_baggage_fields(
                    item,
                    f"{path}[{index}]"
                )

    find_baggage_fields(results)

else:
    print("No flight offers returned.")

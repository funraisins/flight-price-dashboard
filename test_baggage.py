
import json
import pandas as pd

from baggage import extract_booking_options

with open("booking_response.json", "r", encoding="utf-8") as f:
    data = json.load(f)

rows = extract_booking_options(data)

df = pd.DataFrame(rows)

df["With Cabin Bag"] = (
    df["Base Fare (GBP)"] + df["Cabin Bag (GBP)"]
)

df["With Checked Bag"] = (
    df["Base Fare (GBP)"] + df["Checked Bag (GBP)"]
)

df["With Both Bags"] = (
    df["Base Fare (GBP)"]
    + df["Cabin Bag (GBP)"]
    + df["Checked Bag (GBP)"]
)

print(df.to_string(index=False))

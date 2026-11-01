
# baggage.py

# None means the baggage fee has not been verified.
# 0 should only be used when the requested baggage
# allowance is confirmed to be included.

BAGGAGE_FEES = {
    "Ryanair": {
        "cabin": None,
        "checked": None
    },
    "easyJet": {
        "cabin": None,
        "checked": None
    },
    "Iberia": {
        "cabin": None,
        "checked": None
    },
    "British Airways": {
        "cabin": None,
        "checked": None
    },
    "Air Europa": {
        "cabin": None,
        "checked": None
    }
}


def get_baggage_fees(airline):
    """
    Return known additional baggage fees.

    None = unknown fee
    0 = verified included allowance
    Positive number = verified extra fee in GBP
    """

    return BAGGAGE_FEES.get(
        airline,
        {"cabin": None, "checked": None}
    )


def calculate_total_price(
    base_price,
    cabin_fee,
    checked_fee,
    baggage_option
):
    """
    Calculate total price only when all required
    baggage fees are known.
    """

    total = float(base_price)

    if baggage_option in [
        "Cabin baggage",
        "Cabin + Checked baggage"
    ]:
        if cabin_fee is None:
            return None
        total += cabin_fee

    if baggage_option in [
        "Checked baggage",
        "Cabin + Checked baggage"
    ]:
        if checked_fee is None:
            return None
        total += checked_fee

    return total


import re


def parse_baggage_price(text):
    """
    Extract a numeric baggage price.

    Examples:
    '1 carry-on bag: 47' -> 47.0
    '1st checked bag: 54' -> 54.0

    Returns None when no valid price is found.
    """

    if not isinstance(text, str):
        return None

    match = re.search(
        r":\s*(?:£\s*)?(\d+(?:\.\d{1,2})?)\s*$",
        text
    )

    if match:
        return float(match.group(1))

    return None


def extract_booking_options(booking_response):
    """
    Extract booking-provider-specific fares and baggage fees.

    Only processes combined ('together') booking options.
    """

    rows = []

    for option in booking_response.get("booking_options", []):

        together = option.get("together")

        if not isinstance(together, dict):
            continue

        provider = together.get("book_with", "Unknown")
        base_price = together.get("price")

        if base_price is None:
            continue

        cabin_fee = None
        checked_fee = None

        for item in together.get("baggage_prices", []):

            item_lower = item.lower()
            fee = parse_baggage_price(item)

            if "carry-on" in item_lower:
                cabin_fee = fee

            elif "checked bag" in item_lower:
                checked_fee = fee

        rows.append({
            "Booking Provider": provider,
            "Base Fare (GBP)": float(base_price),
            "Cabin Bag (GBP)": cabin_fee,
            "Checked Bag (GBP)": checked_fee
        })

    return rows

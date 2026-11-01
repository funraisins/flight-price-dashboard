
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from flight_api import search_multiple_airports, get_booking_details
from baggage import (
    get_baggage_fees,
    calculate_total_price,
    extract_booking_options
)

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="London to Madrid Flight Finder",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ London → Madrid Flight Finder")
st.caption("Compare real flight prices across London airports using SerpApi")


# --------------------------------------------------
# 2. AIRPORT CONFIGURATION
# --------------------------------------------------

airports = {
    "Heathrow": "LHR",
    "Gatwick": "LGW",
    "Stansted": "STN",
    "Luton": "LTN",
    "London City": "LCY",
    "Southend": "SEN"
}


# --------------------------------------------------
# 3. CACHED API SEARCH
# --------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def cached_search(origin, destination, departure_date):
    """
    Cache each airport search for 30 minutes.
    Identical searches reuse cached results.
    """

    return search_multiple_airports(
        origins=[origin],
        destination=destination,
        departure_date=departure_date
    )


# --------------------------------------------------
# 4. SIDEBAR SEARCH FILTERS
# --------------------------------------------------

st.sidebar.header("Search Flights")

selected_airports = st.sidebar.multiselect(
    "Departure airports",
    options=list(airports.keys()),
    default=["Heathrow", "Gatwick"]
)

departure_date = st.sidebar.date_input(
    "Departure date",
    value=date.today() + timedelta(days=30),
    min_value=date.today()
)

direct_only = st.sidebar.checkbox(
    "Direct flights only",
    value=True
)

st.sidebar.subheader("Baggage Options")

baggage_option = st.sidebar.selectbox(
    "Compare prices with",
    [
        "No extra baggage",
        "Cabin baggage",
        "Checked baggage",
        "Cabin + Checked baggage"
    ]
)

search_clicked = st.sidebar.button(
    "Search Flights",
    type="primary"
)


# --------------------------------------------------
# 5. SEARCH FLIGHTS
# --------------------------------------------------

if "flight_offers" not in st.session_state:
    st.session_state.flight_offers = None

if "search_errors" not in st.session_state:
    st.session_state.search_errors = {}

if "last_search" not in st.session_state:
    st.session_state.last_search = None

if search_clicked:

    airport_codes = [
        airports[name] for name in selected_airports
    ]

    if not airport_codes:
        st.warning("Please select at least one airport.")
        st.stop()

    all_offers = []
    all_errors = {}

    with st.spinner("Searching flights from London..."):

        for origin in airport_codes:

            try:
                offers, errors = cached_search(
                    origin=origin,
                    destination="MAD",
                    departure_date=departure_date.isoformat()
                )

                all_offers.extend(offers)
                all_errors.update(errors)

            except Exception as e:
                all_errors[origin] = str(e)

    st.session_state.flight_offers = all_offers
    st.session_state.search_errors = all_errors
    st.session_state.last_search = {
        "airports": airport_codes,
        "date": departure_date.isoformat()
    }



# --------------------------------------------------
# 6. DISPLAY SEARCH RESULTS
# --------------------------------------------------

offers = st.session_state.flight_offers

if offers is None:
    st.info(
        "Select your departure airports and travel date, "
        "then click Search Flights."
    )
    st.stop()

if st.session_state.search_errors:
    st.warning(
        "Some airport searches failed: "
        + ", ".join(st.session_state.search_errors.keys())
    )

search_info = st.session_state.last_search

if search_info:
    st.caption(
        f"Showing results for {', '.join(search_info['airports'])} "
        f"→ MAD on {search_info['date']}"
    )

flight_rows = []

for offer in offers:
    segments = offer.get("flights", [])

    if not segments:
        continue

    if direct_only and len(segments) != 1:
        continue

    first = segments[0]
    last = segments[-1]

    airline = first.get("airline", "Unknown")
    base_price = offer.get("price")

    if base_price is None:
        continue

    # Get baggage fees from baggage.py
    fees = get_baggage_fees(airline)

    # Calculate total cost for selected baggage
    total_price = calculate_total_price(
        base_price=base_price,
        cabin_fee=fees["cabin"],
        checked_fee=fees["checked"],
        baggage_option=baggage_option
    )

    flight_rows.append({
        "Airline": airline,
        "From": first.get("departure_airport", {}).get("id"),
        "To": last.get("arrival_airport", {}).get("id"),
        "Departure": first.get("departure_airport", {}).get("time"),
        "Arrival": last.get("arrival_airport", {}).get("time"),
        "Duration (min)": offer.get("total_duration"),
        "Base Fare (GBP)": base_price,
        "Cabin Bag (GBP)": fees["cabin"],
        "Checked Bag (GBP)": fees["checked"],
        "Total Price (GBP)": total_price,
        "Booking Token": offer.get("booking_token")
    })


# --------------------------------------------------
# 7. CREATE DATAFRAME
# --------------------------------------------------

if not flight_rows:
    st.warning("No matching flights found.")
    st.stop()

df = pd.DataFrame(flight_rows)

price_columns = [
    "Base Fare (GBP)",
    "Cabin Bag (GBP)",
    "Checked Bag (GBP)",
    "Total Price (GBP)"
]

for column in price_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

df = df.dropna(subset=["Base Fare (GBP)"])

if df.empty:
    st.warning("No flights with valid base fares were returned.")
    st.stop()

df = df.sort_values(
    by=["Total Price (GBP)", "Base Fare (GBP)"],
    ascending=True,
    na_position="last"
).reset_index(drop=True)


# --------------------------------------------------
# 8. SUMMARY METRICS
# --------------------------------------------------

st.subheader("Available Flights")

cheapest_base = df.loc[df["Base Fare (GBP)"].idxmin()]
known_totals = df.dropna(subset=["Total Price (GBP)"])

col1, col2, col3 = st.columns(3)

col1.metric(
    "Cheapest Base Fare",
    f"£{cheapest_base['Base Fare (GBP)']:.2f}"
)

if not known_totals.empty:
    cheapest_total = known_totals.iloc[0]

    col2.metric(
        "Cheapest Total",
        f"£{cheapest_total['Total Price (GBP)']:.2f}"
    )
else:
    col2.metric("Cheapest Total", "Unknown")

col3.metric("Flights Found", len(df))

if known_totals.empty:
    st.warning(
        "Baggage-inclusive totals cannot be calculated "
        "because the required baggage fees are unknown."
    )


# --------------------------------------------------
# 9. FLIGHT COMPARISON TABLE
# --------------------------------------------------

st.subheader("Flight Comparison")

st.dataframe(
    df.drop(columns=["Booking Token"], errors="ignore"),
    width="stretch",
    hide_index=True,
    column_config={
        "Base Fare (GBP)": st.column_config.NumberColumn(
            "Base Fare",
            format="£%.2f"
        ),
        "Cabin Bag (GBP)": st.column_config.NumberColumn(
            "Extra Cabin Bag",
            format="£%.2f"
        ),
        "Checked Bag (GBP)": st.column_config.NumberColumn(
            "Checked Bag",
            format="£%.2f"
        ),
        "Total Price (GBP)": st.column_config.NumberColumn(
            "Total Price",
            format="£%.2f"
        )
    }
)

st.caption(
    "Blank baggage fees indicate unknown prices, "
    "not free baggage."
)


# --------------------------------------------------
# 10. PRICE COMPARISON CHART
# --------------------------------------------------

st.subheader("Flight Price Comparison")

chart_df = df.copy()

chart_df["Flight"] = (
    chart_df["Airline"]
    + " ("
    + chart_df["From"].fillna("?")
    + ") "
    + chart_df["Departure"].fillna("")
)

chart_column = (
    "Total Price (GBP)"
    if not known_totals.empty
    else "Base Fare (GBP)"
)

if known_totals.empty and baggage_option != "No extra baggage":
    st.info(
        "Showing base fares because baggage-inclusive "
        "totals are unavailable."
    )

chart_data = chart_df.dropna(subset=[chart_column])

st.bar_chart(
    chart_data,
    x="Flight",
    y=chart_column
)


# --------------------------------------------------
# 11. CHEAPEST FLIGHT BY AIRPORT
# --------------------------------------------------

st.subheader("Cheapest Base Fare by Airport")

airport_summary = (
    df.groupby("From", as_index=False)["Base Fare (GBP)"]
    .min()
    .sort_values("Base Fare (GBP)")
)

st.dataframe(
    airport_summary,
    width="stretch",
    hide_index=True,
    column_config={
        "Base Fare (GBP)": st.column_config.NumberColumn(
            "Cheapest Base Fare",
            format="£%.2f"
        )
    }
)


# --------------------------------------------------
# 12. DISCLAIMER
# --------------------------------------------------

st.info(
    "Flight prices come from Google Flights via SerpApi "
    "and may change before booking. Baggage fees are "
    "currently unknown unless separately verified. "
    "Blank baggage values must not be interpreted as £0."
)


# --------------------------------------------------
# 13. SELECT A FLIGHT TO CHECK BAGGAGE PRICES
# --------------------------------------------------

st.divider()
st.subheader("Check Baggage Prices for a Flight")

selectable_flights = df.dropna(
    subset=["Booking Token"]
).copy()

if selectable_flights.empty:
    st.warning("No flights with booking tokens available.")

else:
    selectable_flights["Flight Label"] = (
        selectable_flights["Airline"]
        + " | "
        + selectable_flights["From"]
        + " → MAD | "
        + selectable_flights["Departure"].fillna("")
        + " | £"
        + selectable_flights["Base Fare (GBP)"].astype(str)
    )

    selected_index = st.selectbox(
        "Select a flight",
        options=selectable_flights.index,
        format_func=lambda i: selectable_flights.loc[i, "Flight Label"]
    )

    selected_flight = selectable_flights.loc[selected_index]

    @st.cache_data(ttl=1800, show_spinner=False)
    def cached_booking_details(
        origin, destination, departure_date, token
    ):
        return get_booking_details(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            booking_token=token
        )

    if st.button("Check Baggage Prices", type="primary"):

        with st.spinner("Retrieving booking options..."):
            try:
                booking_data = cached_booking_details(
                    origin=selected_flight["From"],
                    destination="MAD",
                    departure_date=search_info["date"],
                    token=selected_flight["Booking Token"]
                )

                booking_rows = extract_booking_options(
                    booking_data
                )

                st.session_state.booking_rows = booking_rows
                st.session_state.booking_flight = (
                    selected_flight["Flight Label"]
                )

            except Exception:
                st.error(
                    "Unable to retrieve booking details. "
                    "Please check your API quota and try again."
                )

    if (
        st.session_state.get("booking_rows") is not None
        and st.session_state.get("booking_flight")
        == selected_flight["Flight Label"]
    ):

        booking_df = pd.DataFrame(
            st.session_state.booking_rows
        )

        if booking_df.empty:
            st.warning("No booking options found.")

        else:
            booking_df["With Cabin Bag"] = (
                booking_df["Base Fare (GBP)"]
                + booking_df["Cabin Bag (GBP)"]
            )

            booking_df["With Checked Bag"] = (
                booking_df["Base Fare (GBP)"]
                + booking_df["Checked Bag (GBP)"]
            )

            booking_df["With Both Bags"] = (
                booking_df["Base Fare (GBP)"]
                + booking_df["Cabin Bag (GBP)"]
                + booking_df["Checked Bag (GBP)"]
            )

            st.subheader("Booking Provider Comparison")

            st.dataframe(
                booking_df,
                width="stretch",
                hide_index=True
            )

            known_totals = booking_df.dropna(
                subset=["With Both Bags"]
            )

            if not known_totals.empty:
                cheapest = known_totals.sort_values(
                    "With Both Bags"
                ).iloc[0]

                st.metric(
                    "Lowest Reported Total With Both Bags",
                    f"£{cheapest['With Both Bags']:.2f}"
                )

                st.caption(
                    f"Provider: {cheapest['Booking Provider']}"
                )

            else:
                st.warning(
                    "No booking provider returned both "
                    "cabin and checked baggage prices."
                )

            st.caption(
                "Blank baggage fees mean the provider did "
                "not report a fee. They do not mean baggage "
                "is included. Confirm baggage allowances, "
                "currency and final charges before booking."
            )

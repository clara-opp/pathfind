import sqlite3
import pandas as pd
import streamlit as st

# Configuration: path to your SQLite database
DB_PATH = "numbeo.db"


# ---------- Helper functions for database access ----------

@st.cache_data
def get_table_names() -> list[str]:
    """Return a list of table names in the SQLite database."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;",
            conn,
        )
    return df["name"].tolist()


@st.cache_data
def load_table(table_name: str) -> pd.DataFrame:
    """Load a full table from the SQLite database into a DataFrame."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(f"SELECT * FROM {table_name};", conn)
    return df


@st.cache_data
def load_country_prices_joined() -> pd.DataFrame:
    """Load a joined view of country_prices with country and item names."""
    query = """
        SELECT
            cp.country_id,
            c.country_name,
            c.currency,
            cp.item_id,
            i.item_name,
            cp.average_price,
            cp.lowest_price,
            cp.highest_price,
            cp.data_points
        FROM country_prices cp
        JOIN countries c ON cp.country_id = c.country_id
        JOIN items i ON cp.item_id = i.item_id
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(query, conn)
    return df


@st.cache_data
def get_countries() -> list[str]:
    """Get a sorted list of available country names."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(
            "SELECT country_name FROM countries ORDER BY country_name;",
            conn,
        )
    return df["country_name"].tolist()


def get_price_for_item(
    conn: sqlite3.Connection,
    country_name: str,
    item_pattern: str,
) -> float | None:
    """Get average_price for an item in a given country using a LIKE pattern."""
    query = """
        SELECT cp.average_price, i.item_name
        FROM country_prices cp
        JOIN countries c ON cp.country_id = c.country_id
        JOIN items i ON cp.item_id = i.item_id
        WHERE c.country_name = ?
          AND i.item_name LIKE ?
        LIMIT 1;
    """
    df = pd.read_sql(query, conn, params=(country_name, item_pattern + "%"))
    if df.empty:
        return None
    return float(df.loc[0, "average_price"])


def get_eur_conversion_factor(conn: sqlite3.Connection, currency: str) -> float:
    """Return factor to convert local price to EUR (price_local / one_eur_to_currency)."""
    query = """
        SELECT one_eur_to_currency
        FROM exchange_rates
        WHERE currency_code = ?
        LIMIT 1;
    """
    df = pd.read_sql(query, conn, params=(currency,))
    if df.empty or pd.isna(df.loc[0, "one_eur_to_currency"]):
        # Fallback: treat as already EUR if we do not know the conversion
        return 1.0
    return float(df.loc[0, "one_eur_to_currency"])


def load_country_currency(conn: sqlite3.Connection, country_name: str) -> str:
    """Get the currency code for a given country."""
    df = pd.read_sql(
        "SELECT currency FROM countries WHERE country_name = ? LIMIT 1;",
        conn,
        params=(country_name,),
    )
    if df.empty:
        return "EUR"
    return df.loc[0, "currency"]


# ---------- UI: Data Explorer mode ----------

def data_explorer_ui():
    """Simple UI to explore raw tables and a joined country_prices view."""
    st.header("Numbeo Data Explorer")

    base_tables = get_table_names()
    extra_views = ["country_prices_joined"]

    selection = st.sidebar.selectbox(
        "Select table or view",
        options=base_tables + extra_views,
        index=0,
    )

    # Load selected data
    if selection == "country_prices_joined":
        df = load_country_prices_joined()
    else:
        df = load_table(selection)

    st.subheader(f"Table/View: {selection}")
    st.write(f"Rows: {len(df)}, Columns: {len(df.columns)}")

    # Special handling for the joined prices view
    if selection == "country_prices_joined":
        st.sidebar.subheader("Filters (country_prices_joined)")

        # Country filter
        countries = sorted(df["country_name"].dropna().unique().tolist())
        selected_countries = st.sidebar.multiselect(
            "Filter by country",
            options=countries,
            default=[],
        )

        # Item name filter (simple substring search)
        item_search = st.sidebar.text_input(
            "Filter item_name (substring)",
            value="",
            help="Example: 'Gasoline', 'Meal', 'Beer'",
        )

        # Apply filters
        filtered = df.copy()
        if selected_countries:
            filtered = filtered[filtered["country_name"].isin(selected_countries)]
        if item_search:
            filtered = filtered[
                filtered["item_name"].str.contains(
                    item_search, case=False, na=False
                )
            ]

        st.write(f"Filtered rows: {len(filtered)}")
        st.dataframe(filtered, use_container_width=True)

        # Simple summary statistics
        if "average_price" in filtered.columns and not filtered.empty:
            st.subheader("Summary statistics (average_price)")
            st.write(filtered["average_price"].describe())
    else:
        # Generic view for all other tables
        st.dataframe(df, use_container_width=True)

        # Show basic summary statistics if numeric columns exist
        num_cols = df.select_dtypes(include="number").columns
        if len(num_cols) > 0:
            st.subheader("Summary statistics (numeric columns)")
            st.write(df[num_cols].describe())


# ---------- UI: Trip Cost Estimator mode ----------

def cost_estimator_ui():
    """Simple trip cost estimator UI based on user inputs and Numbeo data."""
    st.header("Trip Cost Estimator")

    countries = get_countries()
    if not countries:
        st.error("No countries found in database.")
        return

    country = st.selectbox("Select country", options=countries)
    days = st.number_input("Number of days", min_value=1, value=7)
    persons = st.number_input("Number of travelers", min_value=1, value=2)

    st.subheader("Daily consumption per person")
    meals_per_day = st.number_input(
        "Restaurant meals per day",
        min_value=0.0,
        value=1.0,
        step=0.5,
    )
    beers_per_day = st.number_input(
        "Beers (0.5L, restaurant or bar) per day",
        min_value=0.0,
        value=1.0,
        step=0.5,
    )
    local_tickets_per_day = st.number_input(
        "Local transport one-way tickets per day",
        min_value=0.0,
        value=1.0,
        step=0.5,
    )

    st.subheader("Accommodation")
    nights = st.number_input("Number of nights", min_value=1, value=7)
    hotel_type = st.selectbox(
        "Accommodation type (proxy)",
        options=[
            "1 Bedroom Apartment in City Centre",
            "1 Bedroom Apartment Outside of City Centre",
            "3 Bedroom Apartment in City Centre",
            "3 Bedroom Apartment Outside of City Centre",
        ],
    )

    # Open a fresh DB connection for price lookups
    conn = sqlite3.connect(DB_PATH)

    # Fetch prices from DB using simple LIKE patterns
    meal_price = get_price_for_item(
        conn, country, "Meal at an Inexpensive Restaurant"
    )
    beer_price = get_price_for_item(
        conn, country, "Domestic Draft Beer (0.5 Liter)"
    )
    ticket_price = get_price_for_item(
        conn, country, "One-Way Ticket (Local Transport)"
    )

    hotel_pattern_map = {
        "1 Bedroom Apartment in City Centre": "1 Bedroom Apartment in City Centre",
        "1 Bedroom Apartment Outside of City Centre": "1 Bedroom Apartment Outside of City Centre",
        "3 Bedroom Apartment in City Centre": "3 Bedroom Apartment in City Centre",
        "3 Bedroom Apartment Outside of City Centre": "3 Bedroom Apartment Outside of City Centre",
    }
    hotel_price_month = get_price_for_item(
        conn, country, hotel_pattern_map[hotel_type]
    )

    currency = load_country_currency(conn, country)
    eur_factor = get_eur_conversion_factor(conn, currency)

    if st.button("Estimate trip cost"):
        # Convert monthly apartment price (approx) to nightly price
        nights_in_month = 30.0
        hotel_price_per_night = (hotel_price_month or 0.0) / nights_in_month

        daily_food_cost_per_person = (meal_price or 0.0) * meals_per_day
        daily_beer_cost_per_person = (beer_price or 0.0) * beers_per_day
        daily_transport_cost_per_person = (ticket_price or 0.0) * local_tickets_per_day

        daily_cost_per_person = (
            daily_food_cost_per_person
            + daily_beer_cost_per_person
            + daily_transport_cost_per_person
        )

        total_variable_cost_local = daily_cost_per_person * days * persons
        total_accommodation_cost_local = hotel_price_per_night * nights
        total_local = total_variable_cost_local + total_accommodation_cost_local

        total_eur = total_local / eur_factor if eur_factor else total_local

        st.subheader("Estimated trip cost")
        st.write(f"**Local currency ({currency})**: {total_local:,.2f}")
        st.write(f"**In EUR (approx.)**: {total_eur:,.2f}")

        st.markdown("**Assumptions:**")
        st.markdown(
            "- Accommodation based on monthly apartment price, converted to nightly rate.\n"
            "- Prices use Numbeo average_price values.\n"
            "- Transport and restaurant usage based on your daily input."
        )

    conn.close()


# ---------- Main app ----------

def main():
    st.title("Numbeo Travel Dashboard")

    mode = st.sidebar.selectbox(
        "Select mode",
        ["Data Explorer", "Trip Cost Estimator"],
    )

    if mode == "Data Explorer":
        data_explorer_ui()
    elif mode == "Trip Cost Estimator":
        cost_estimator_ui()


if __name__ == "__main__":
    main()

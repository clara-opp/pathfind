import sqlite3
import pandas as pd
import streamlit as st

# Configuration: path to your SQLite database
DB_PATH = "numbeo.db"


@st.cache_data
def get_table_names() -> list[str]:
    """Return a list of table names in the SQLite database."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;", conn)
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


def main():
    # Title and basic description
    st.title("Numbeo Data Explorer")
    st.write("Simple Streamlit app to explore the Numbeo SQLite database.")

    # Sidebar: table selection
    st.sidebar.header("Navigation")

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

    # Optional filters for the joined prices table
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
            filtered = filtered[filtered["item_name"].str.contains(item_search, case=False, na=False)]

        st.write(f"Filtered rows: {len(filtered)}")
        st.dataframe(filtered, use_container_width=True)

        # Simple summary statistics
        if "average_price" in filtered.columns and not filtered.empty:
            st.subheader("Summary statistics (average_price)")
            st.write(filtered["average_price"].describe())

    else:
        # Generic view for other tables
        st.dataframe(df, use_container_width=True)

        # Show basic summary statistics if numeric columns exist
        num_cols = df.select_dtypes(include="number").columns
        if len(num_cols) > 0:
            st.subheader("Summary statistics (numeric columns)")
            st.write(df[num_cols].describe())


if __name__ == "__main__":
    main()

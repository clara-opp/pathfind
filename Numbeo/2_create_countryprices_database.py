import os
import sqlite3
import pandas as pd

# Configuration: define input CSV file and output SQLite database file
CSV_PATH = "numbeo_country_prices_preview.csv"
DB_PATH = "numbeo.db"


def load_prices(csv_path: str) -> pd.DataFrame:
    """Load the combined Numbeo country prices CSV into a pandas DataFrame."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input CSV not found at: {csv_path}")
    df = pd.read_csv(csv_path)
    return df


def build_countries_table(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Create a countries dimension table with a simple integer primary key."""
    countries_df = (
        prices_df[["country_name", "currency"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    countries_df["country_id"] = countries_df.index + 1
    return countries_df[["country_id", "country_name", "currency"]]


def build_items_table(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Create an items dimension table from unique item_id / item_name pairs."""
    items_df = (
        prices_df[["item_id", "item_name"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return items_df[["item_id", "item_name"]]


def build_country_prices_table(
    prices_df: pd.DataFrame, countries_df: pd.DataFrame
) -> pd.DataFrame:
    """Create a normalized fact table linking countries to items with price data."""
    merged = prices_df.merge(
        countries_df, on="country_name", how="left"
    )
    country_prices_df = merged[
        [
            "country_id",
            "item_id",
            "average_price",
            "lowest_price",
            "highest_price",
            "data_points",
        ]
    ].copy()
    return country_prices_df


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the SQLite tables for countries, items and country_prices if needed."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS countries (
            country_id INTEGER PRIMARY KEY,
            country_name TEXT NOT NULL,
            currency TEXT
        );

        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS country_prices (
            country_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            average_price REAL,
            lowest_price REAL,
            highest_price REAL,
            data_points INTEGER,
            PRIMARY KEY (country_id, item_id),
            FOREIGN KEY (country_id) REFERENCES countries(country_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        );
        """
    )


def write_tables_to_db(
    conn: sqlite3.Connection,
    countries_df: pd.DataFrame,
    items_df: pd.DataFrame,
    country_prices_df: pd.DataFrame,
) -> None:
    """Write the pandas DataFrames into the corresponding SQLite tables."""
    countries_df.to_sql(
        "countries", conn, if_exists="replace", index=False
    )
    items_df.to_sql(
        "items", conn, if_exists="replace", index=False
    )
    country_prices_df.to_sql(
        "country_prices", conn, if_exists="replace", index=False
    )


if __name__ == "__main__":
    # Step 1: load the previously exported Numbeo prices CSV
    prices_df = load_prices(CSV_PATH)
    print(f"Loaded prices_df with shape: {prices_df.shape}")

    # Step 2: build dimension tables (countries and items)
    countries_df = build_countries_table(prices_df)
    items_df = build_items_table(prices_df)
    print(f"Countries: {len(countries_df)}, Items: {len(items_df)}")

    # Step 3: build the normalized country_prices fact table
    country_prices_df = build_country_prices_table(prices_df, countries_df)
    print(f"country_prices_df shape: {country_prices_df.shape}")

    # Step 4: open SQLite connection and create schema
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    # Step 5: write all tables into the SQLite database
    with conn:
        write_tables_to_db(conn, countries_df, items_df, country_prices_df)

    conn.close()
    print(f"\nSQLite database '{DB_PATH}' created with tables: countries, items, country_prices.")

import os
import sqlite3
import requests
import pandas as pd

# Basic configuration: API, base URL, database path
API_KEY = os.environ.get("NUMBEO_API_KEY")
BASE_URL = "https://www.numbeo.com/api"
DB_PATH = "numbeo.db"

if not API_KEY:
    raise RuntimeError("NUMBEO_API_KEY is not set; make sure it is defined in your .env or environment.")


def get_json(endpoint: str, params: dict | None = None) -> dict:
    """Send a GET request to a Numbeo API endpoint and return the JSON response."""
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Numbeo API error for endpoint '{endpoint}': {data['error']}")
    return data


def load_countries(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load country_id and country_name from the countries table."""
    df = pd.read_sql("SELECT country_id, country_name FROM countries;", conn)
    if df.empty:
        raise RuntimeError("countries table is empty; make sure the base ETL has run.")
    return df


def fetch_country_indices_for_name(country_name: str) -> dict:
    """Fetch Numbeo country_indices for a given country name."""
    data = get_json("country_indices", {"country": country_name})
    data["country_name"] = data.get("name", country_name)
    return data


def create_country_indices_table(conn: sqlite3.Connection) -> None:
    """Create the country_indices table in SQLite if it does not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS country_indices (
            country_id INTEGER PRIMARY KEY,
            country_name TEXT,
            health_care_index REAL,
            crime_index REAL,
            traffic_time_index REAL,
            purchasing_power_incl_rent_index REAL,
            cpi_index REAL,
            pollution_index REAL,
            traffic_index REAL,
            quality_of_life_index REAL,
            cpi_and_rent_index REAL,
            groceries_index REAL,
            safety_index REAL,
            rent_index REAL,
            traffic_co2_index REAL,
            restaurant_price_index REAL,
            traffic_inefficiency_index REAL,
            property_price_to_income_ratio REAL,
            FOREIGN KEY (country_id) REFERENCES countries(country_id)
        );
        """
    )


def insert_country_indices(conn: sqlite3.Connection, idx: dict, country_id: int) -> None:
    """Insert or replace a single country's indices into the country_indices table."""
    # Map each expected key from the API dictionary using .get for safety
    params = {
        "country_id": country_id,
        "country_name": idx.get("country_name"),
        "health_care_index": idx.get("health_care_index"),
        "crime_index": idx.get("crime_index"),
        "traffic_time_index": idx.get("traffic_time_index"),
        "purchasing_power_incl_rent_index": idx.get("purchasing_power_incl_rent_index"),
        "cpi_index": idx.get("cpi_index"),
        "pollution_index": idx.get("pollution_index"),
        "traffic_index": idx.get("traffic_index"),
        "quality_of_life_index": idx.get("quality_of_life_index"),
        "cpi_and_rent_index": idx.get("cpi_and_rent_index"),
        "groceries_index": idx.get("groceries_index"),
        "safety_index": idx.get("safety_index"),
        "rent_index": idx.get("rent_index"),
        "traffic_co2_index": idx.get("traffic_co2_index"),
        "restaurant_price_index": idx.get("restaurant_price_index"),
        "traffic_inefficiency_index": idx.get("traffic_inefficiency_index"),
        "property_price_to_income_ratio": idx.get("property_price_to_income_ratio"),
    }

    conn.execute(
        """
        INSERT OR REPLACE INTO country_indices (
            country_id,
            country_name,
            health_care_index,
            crime_index,
            traffic_time_index,
            purchasing_power_incl_rent_index,
            cpi_index,
            pollution_index,
            traffic_index,
            quality_of_life_index,
            cpi_and_rent_index,
            groceries_index,
            safety_index,
            rent_index,
            traffic_co2_index,
            restaurant_price_index,
            traffic_inefficiency_index,
            property_price_to_income_ratio
        ) VALUES (
            :country_id,
            :country_name,
            :health_care_index,
            :crime_index,
            :traffic_time_index,
            :purchasing_power_incl_rent_index,
            :cpi_index,
            :pollution_index,
            :traffic_index,
            :quality_of_life_index,
            :cpi_and_rent_index,
            :groceries_index,
            :safety_index,
            :rent_index,
            :traffic_co2_index,
            :restaurant_price_index,
            :traffic_inefficiency_index,
            :property_price_to_income_ratio
        );
        """,
        params,
    )


if __name__ == "__main__":
    # Step 1: open database and load all countries
    conn = sqlite3.connect(DB_PATH)
    countries_df = load_countries(conn)
    print(f"Loaded {len(countries_df)} countries from database.")

    # Step 2: ensure the country_indices table exists
    create_country_indices_table(conn)

    # Step 3: loop over countries and fetch + insert indices
    with conn:
        for _, row in countries_df.iterrows():
            country_id = int(row["country_id"])
            country_name = row["country_name"]
            try:
                idx = fetch_country_indices_for_name(country_name)
                insert_country_indices(conn, idx, country_id)
                print(f"OK: indices stored for {country_name}")
            except Exception as e:
                print(f"Error for {country_name}: {e}")

    conn.close()
    print(f"\ncountry_indices table has been updated in '{DB_PATH}'.")

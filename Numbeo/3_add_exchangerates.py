import os
import sqlite3
import requests
import pandas as pd

# Basic configuration: read API key and set base URL and DB path
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


def fetch_exchange_rates() -> pd.DataFrame:
    """Fetch Numbeo currency exchange rates and return them as a DataFrame."""
    data = get_json("currency_exchange_rates")
    if "exchange_rates" not in data:
        raise RuntimeError(f"Unexpected response structure: {data}")
    df = pd.DataFrame(data["exchange_rates"])
    df.rename(
        columns={
            "currency": "currency_code",
            "one_usd_to_currency": "one_usd_to_currency",
            "one_eur_to_currency": "one_eur_to_currency",
        },
        inplace=True,
    )
    return df[["currency_code", "one_usd_to_currency", "one_eur_to_currency"]]


def create_exchange_rate_table(conn: sqlite3.Connection) -> None:
    """Create the exchange_rates table in SQLite if it does not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS exchange_rates (
            currency_code TEXT PRIMARY KEY,
            one_usd_to_currency REAL,
            one_eur_to_currency REAL
        );
        """
    )


def write_exchange_rates(conn: sqlite3.Connection, rates_df: pd.DataFrame) -> None:
    """Write the exchange rates DataFrame into the exchange_rates table."""
    rates_df.to_sql(
        "exchange_rates",
        conn,
        if_exists="replace",
        index=False,
    )


if __name__ == "__main__":
    # Step 1: fetch exchange rates from Numbeo
    rates_df = fetch_exchange_rates()
    print(f"Fetched {len(rates_df)} exchange rates from Numbeo.")

    # Step 2: open SQLite DB and create table if needed
    conn = sqlite3.connect(DB_PATH)
    create_exchange_rate_table(conn)

    # Step 3: write exchange rates to the database
    with conn:
        write_exchange_rates(conn, rates_df)

    conn.close()
    print(f"Exchange rates written to 'exchange_rates' table in '{DB_PATH}'.")

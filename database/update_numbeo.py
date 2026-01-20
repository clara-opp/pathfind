"""
update_numbeo.py
----------------
Updates ONLY these two CSVs in ./data:
  - numbeo_exchange_rates.csv
  - numbeo_country_indices.csv

Reads (must already exist) in ./data:
  - numbeo_countries.csv  (needs columns: country_name, iso3)

Requirements:
  pip install requests pandas python-dotenv

Env:
  .env must contain: NUMBEO_API_KEY=...

Run:
  python update_numbeo.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

import requests
import pandas as pd
from dotenv import load_dotenv


# =========================
# Config
# =========================
BASE_URL = "https://www.numbeo.com/api"
TIMEOUT_SECONDS = 30


# =========================
# Paths (always relative to this script)
# =========================
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# Env / API Key
# =========================
load_dotenv()
API_KEY = os.environ.get("NUMBEO_API_KEY")

if not API_KEY:
    raise RuntimeError("NUMBEO_API_KEY is not set; define it in .env or your environment.")


def get_json(endpoint: str, params: Optional[dict] = None) -> Dict[str, Any]:
    """Generic helper to call a Numbeo API endpoint and return JSON."""
    if params is None:
        params = {}
    params = dict(params)
    params["api_key"] = API_KEY

    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        params=params,
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Numbeo API error for endpoint '{endpoint}': {data['error']}")

    return data


def fetch_exchange_rates() -> pd.DataFrame:
    """Fetch currency exchange rates from Numbeo into a DataFrame."""
    data = get_json("currency_exchange_rates")
    if "exchange_rates" not in data:
        raise RuntimeError(f"Unexpected response for currency_exchange_rates: {data}")
    return pd.DataFrame(data["exchange_rates"])


def fetch_country_indices_all() -> pd.DataFrame:
    """
    Fetch country-level indices for all countries listed in data/numbeo_countries.csv.
    Uses iso3 as query parameter where possible.
    """
    countries_path = DATA_DIR / "numbeo_countries.csv"
    if not countries_path.exists():
        raise FileNotFoundError(
            f"Missing '{countries_path}'. "
            "Generate it once with your full Numbeo fetch script before using this updater."
        )

    countries_df = pd.read_csv(countries_path)

    rows: list[dict] = []

    for _, row in countries_df.iterrows():
        iso3 = row.get("iso3")
        base_name = row.get("country_name")

        if pd.isna(iso3):
            print(f"Skipping {base_name}: no iso3 mapping.")
            continue

        try:
            data = get_json("country_indices", {"country": iso3})
        except Exception as e:
            print(f"Error fetching indices for {iso3} / {base_name}: {e}")
            continue

        rows.append(
            {
                "iso3": iso3,
                "country_name": data.get("name", base_name),
                "cost_of_living_index": data.get("cpi_index"),
                "cpi_and_rent_index": data.get("cpi_and_rent_index"),
                "rent_index": data.get("rent_index"),
                "groceries_index": data.get("groceries_index"),
                "restaurant_price_index": data.get("restaurant_price_index"),
                "purchasing_power_incl_rent_index": data.get("purchasing_power_incl_rent_index"),
                "quality_of_life_index": data.get("quality_of_life_index"),
                "safety_index": data.get("safety_index"),
                "health_care_index": data.get("health_care_index"),
                "pollution_index": data.get("pollution_index"),
                "property_price_to_income_ratio": data.get("property_price_to_income_ratio"),
                "year_last_update": data.get("yearLastUpdate"),
            }
        )

        print(f"OK indices: {iso3} / {base_name}")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # 1) Exchange rates
    try:
        rates_df = fetch_exchange_rates()
        rates_df.to_csv(DATA_DIR / "numbeo_exchange_rates.csv", index=False)
        print("Saved exchange rates to 'data/numbeo_exchange_rates.csv'.")
    except Exception as e:
        print(f"Error fetching exchange rates: {e}")

    # 2) Country indices
    try:
        indices_df = fetch_country_indices_all()
        indices_df.to_csv(DATA_DIR / "numbeo_country_indices.csv", index=False)
        print("Saved country indices to 'data/numbeo_country_indices.csv'.")
        print("Shape:", indices_df.shape)
    except Exception as e:
        print(f"Error fetching country indices: {e}")

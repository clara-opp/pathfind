import os
import requests
import pandas as pd

# Basic configuration: read API key from .env / environment and define base URL
API_KEY = os.environ.get("NUMBEO_API_KEY")
BASE_URL = "https://www.numbeo.com/api"

# Fail early if the API key is not available
if not API_KEY:
    raise RuntimeError("NUMBEO_API_KEY is not set; make sure it is defined in your .env file or environment.")


def get_json(endpoint: str, params: dict | None = None) -> dict:
    """Send a GET request to a Numbeo API endpoint and return the JSON response as a dict."""
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Numbeo API error for endpoint '{endpoint}': {data['error']}")
    return data


def get_country_prices(country: str) -> pd.DataFrame:
    """Fetch latest price data for a given country and return it as a tidy pandas DataFrame."""
    data = get_json("country_prices", {"country": country})
    if "prices" not in data:
        raise RuntimeError(f"Response for country '{country}' does not contain 'prices': {data}")
    df = pd.DataFrame(data["prices"])
    df["country_name"] = data["name"]
    df["currency"] = data["currency"]
    return df


def get_numbeo_countries() -> list[str]:
    """Retrieve all cities from Numbeo and derive the unique list of country names."""
    data = get_json("cities")
    countries = sorted({row["country"] for row in data["cities"]})
    return countries


if __name__ == "__main__":
    # Step 1: quick sanity check for a single country (Germany)
    df_de = get_country_prices("DEU")  # "DEU" or "Germany" both work here
    print("Sample for DEU:")
    print(df_de.head(), "\n")

    # Step 2: get the list of all countries known to Numbeo via the cities endpoint
    countries = get_numbeo_countries()
    print(f"Found {len(countries)} countries in Numbeo.\n")

    # Step 3: loop over all countries and collect all price tables into one list
    all_price_frames: list[pd.DataFrame] = []

    for country in countries:
        try:
            df_country = get_country_prices(country)
            df_country["country_param_used"] = country  # keep track of the exact parameter we sent
            all_price_frames.append(df_country)
            print(f"OK: {country} ({len(df_country)} items)")
        except Exception as e:
            print(f"Error for {country}: {e}")

    # Step 4: combine all country DataFrames into one big DataFrame
    if all_price_frames:
        prices_df = pd.concat(all_price_frames, ignore_index=True)
        print("\nCombined prices_df shape:", prices_df.shape)
        print(prices_df.head())

        # Step 5: save a first snapshot to disk so we can inspect it later
        prices_df.to_csv("numbeo_country_prices_preview.csv", index=False)
        print("\nSaved combined prices to 'numbeo_country_prices_preview.csv'.")
    else:
        print("No price data was collected; check logs above for errors.")

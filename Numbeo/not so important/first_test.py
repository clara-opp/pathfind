import os
import requests
import pandas as pd

# Configuration: read API key from environment and define base URL for all requests
API_KEY = os.environ.get("NUMBEO_API_KEY")
BASE_URL = "https://www.numbeo.com/api"

if not API_KEY:
    raise RuntimeError("NUMBEO_API_KEY is not set in the environment. Export it in your terminal first.")

def get_json(endpoint: str, params: dict | None = None) -> dict:
    """Send a GET request to a Numbeo API endpoint and return the JSON response."""
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    response.raise_for_status()
    return response.json()


def get_country_prices(country: str) -> pd.DataFrame:
    """Fetch latest price data for a given country and return it as a pandas DataFrame."""
    data = get_json("country_prices", {"country": country})
    df = pd.DataFrame(data["prices"])
    df["country_name"] = data["name"]
    df["currency"] = data["currency"]
    return df


if __name__ == "__main__":
    # Simple test: fetch prices for Germany and print the first rows
    df_de = get_country_prices("DEU")  # "DEU" or "Germany" both work
    print(df_de.head())
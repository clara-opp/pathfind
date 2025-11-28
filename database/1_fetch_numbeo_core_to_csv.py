import os
import requests
import pandas as pd
from iso3_map import ISO3_MAP
from dotenv import load_dotenv   

load_dotenv()                    


API_KEY = os.environ.get("NUMBEO_API_KEY")
BASE_URL = "https://www.numbeo.com/api"

if not API_KEY:
    raise RuntimeError("NUMBEO_API_KEY is not set; define it in .env or your environment.")


def get_json(endpoint: str, params: dict | None = None) -> dict:
    """Generic helper to call a Numbeo API endpoint and return JSON."""
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Numbeo API error for endpoint '{endpoint}': {data['error']}")
    return data


def get_country_prices(country_param: str) -> pd.DataFrame:
    """
    Fetch latest price data for a given country and return it as a DataFrame.
    `country_param` can be an ISO code (e.g., 'DEU') or a country name as Numbeo expects it.
    """
    data = get_json("country_prices", {"country": country_param})
    if "prices" not in data:
        raise RuntimeError(f"Response for country '{country_param}' does not contain 'prices': {data}")
    df = pd.DataFrame(data["prices"])
    df["country_name"] = data["name"]
    df["currency"] = data["currency"]
    return df


def get_numbeo_countries() -> list[str]:
    """Retrieve all cities and derive the unique list of country names."""
    data = get_json("cities")
    countries = sorted({row["country"] for row in data["cities"]})
    return countries


if __name__ == "__main__":
    # Quick sanity check
    df_de = get_country_prices("DEU")
    print("Sample for DEU:")
    print(df_de.head(), "\n")

    countries = get_numbeo_countries()
    print(f"Found {len(countries)} countries in Numbeo.\n")

    all_price_frames: list[pd.DataFrame] = []
    country_rows: list[dict] = []

    for country_param in countries:
        try:
            df_country = get_country_prices(country_param)
            country_name = df_country["country_name"].iloc[0]
            currency = df_country["currency"].iloc[0]
            iso3 = ISO3_MAP.get(country_name)

            df_country["country_param_used"] = country_param
            df_country["iso3"] = iso3

            all_price_frames.append(df_country)

            country_rows.append(
                {
                    "country_name": country_name,
                    "country_param_used": country_param,
                    "currency": currency,
                    "iso3": iso3,
                }
            )

            print(f"OK: {country_name} (param='{country_param}', iso3={iso3}, {len(df_country)} items)")
        except Exception as e:
            print(f"Error for {country_param}: {e}")

    if all_price_frames:
        prices_df = pd.concat(all_price_frames, ignore_index=True)
        print("\nCombined prices_df shape:", prices_df.shape)
        print(prices_df.head())

        prices_df.to_csv("numbeo_country_prices.csv", index=False)
        print("\nSaved combined prices to 'numbeo_country_prices.csv'.")

        countries_df = (
            pd.DataFrame(country_rows)
            .drop_duplicates(subset=["country_name"])
            .sort_values("country_name")
        )
        countries_df.to_csv("numbeo_countries.csv", index=False)
        print("Saved countries metadata to 'numbeo_countries.csv'.")
    else:
        print("No price data was collected; check logs for errors.")

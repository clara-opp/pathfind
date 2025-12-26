import pandas as pd
import os
import datetime
import time
from pathlib import Path
from dotenv import load_dotenv

# Assumes amadeus_api_client is now in the same 'database' folder
import amadeus_api_client as amadeus

def get_flight_network_data(airports_df):
    """
    Generates flight prices from US/DE to all other countries.
    
    Logic:
    1. Selects the single busiest airport for every country in the dataset.
    2. Uses the busiest US airport and busiest DE airport as origins.
    3. Fetches flight prices to all other identified major airports.
    """
    # 1. Setup Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    cache_file = data_dir / "flight_network_data.json"

    # 2. Check Cache
    if cache_file.exists():
        print(f"  Using cached flight network data from {cache_file}")
        try:
            return pd.read_json(cache_file)
        except ValueError:
            print("  ⚠️ Error reading cached JSON. Re-fetching data...")

    print("  Cache not found. Fetching live flight prices (this takes ~2-3 mins)...")

    # 3. Load Env (Look in parent directory for .env)
    load_dotenv(script_dir.parent / ".env")
    
    AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
    AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
    
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        print("  ❌ Error: Amadeus credentials not found in .env")
        return pd.DataFrame()

    # 4. Define Origins and Destinations
    try:
        # Filter: Group by Country (iso2) and take the single airport with highest passenger_volume
        # This ensures we have exactly one destination per country (approx 200 total)
        top_airports_per_country = airports_df.sort_values(
            by='passenger_volume', ascending=False
        ).groupby('iso2').head(1)

        print(f"  Identified {len(top_airports_per_country)} major country hubs.")

        # Get the busiest airport for US and DE from this filtered list
        us_row = top_airports_per_country[top_airports_per_country['iso2'] == 'US']
        de_row = top_airports_per_country[top_airports_per_country['iso2'] == 'DE']

        if us_row.empty or de_row.empty:
            print("  ⚠️ Error: Could not find airports for US or Germany in airport data.")
            return pd.DataFrame()

        us_origin = us_row.iloc[0]['iata_code']
        de_origin = de_row.iloc[0]['iata_code']
        
        # The destinations list is now strictly one airport per country
        destinations = top_airports_per_country['iata_code'].tolist()

    except Exception as e:
        print(f"  ❌ Error identifying origins/destinations: {e}")
        return pd.DataFrame()

    print(f"  Origins selected: {us_origin} (US) and {de_origin} (DE)")

    # 5. Generate Routes
    routes = []
    
    for dest in destinations:
        # Route from US Origin -> Destination
        if dest != us_origin:
            routes.append((us_origin, dest))
        
        # Route from DE Origin -> Destination
        if dest != de_origin:
            routes.append((de_origin, dest))

    total_routes = len(routes)
    
    # 6. Authenticate
    token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
    if not token: return pd.DataFrame()

    # 7. Set Dates (90 days out, 1 week trip)
    today = datetime.date.today()
    departure_date = today + datetime.timedelta(days=90)
    return_date = departure_date + datetime.timedelta(days=7)

    results = []
    
    # 8. Fetch Data
    for i, (origin, destination) in enumerate(routes):
        # Print progress every 10 requests
        if i % 10 == 0:
            print(f"  Fetching route {i+1}/{total_routes}...", end="\r")

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date.strftime("%Y-%m-%d"),
            "returnDate": return_date.strftime("%Y-%m-%d"),
            "adults": 1,
            "nonStop": "false", # Allow layovers to find cheapest option
            "currencyCode": "EUR",
            "max": 1
        }

        try:
            response = amadeus.search_flight_offers(token, params)

            if response is None:
                # Refresh token if it expired (401) or a rate limit (429) occurred
                token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                response = amadeus.search_flight_offers(token, params)
            
            if response and 'data' in response and len(response['data']) > 0:
                cheapest = response['data'][0]
                price = float(cheapest['price']['total'])
                
                itineraries = cheapest.get('itineraries', [])
                stops_outbound = len(itineraries[0]['segments']) - 1 if itineraries else 0
                is_direct = (stops_outbound == 0)
                
                results.append({
                    "origin": origin,
                    "destination": destination,
                    "price_eur": price,
                    "is_direct": is_direct,
                    "stops": stops_outbound
                })
        except Exception:
            pass # Skip errors/timeouts to keep moving
        
        time.sleep(5) # Rate limit

    print(f"  Fetch complete. Found prices for {len(results)} routes.")

    # 9. Save and Return
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        # Save as JSON
        df_results.to_json(cache_file, orient='records', indent=4)
        print(f"  ✅ Flight data cached to {cache_file}")
    
    return df_results
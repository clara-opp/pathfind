import requests
     
def get_amadeus_access_token(api_key, api_secret):
    """
    Gets an access token from the Amadeus API.
    """
    if not api_key or not api_secret:
        print("Error: AMADEUS_API_KEY and AMADEUS_API_SECRET must be set in the .env file.")
        return None

    token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": api_secret,
    }
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        return token_response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting access token: {e}")
        return None

def search_flight_offers(access_token, flight_params):
    """
    Searches for flight offers using the Amadeus API.
    """
    search_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # Dynamically build the search parameters from what GPT extracted
    params = {
        "originLocationCode": flight_params["originLocationCode"],
        "destinationLocationCode": flight_params["destinationLocationCode"],
        "departureDate": flight_params.get("departureDate"),
        "adults": flight_params.get("adults", 1), # Default to 1 adult if not specified
        "max": 5
     }
    # Add optional parameters if they exist
    for param in ["children", "infants", "nonStop"]:
        if param in flight_params:
            # Amadeus API expects booleans as lowercase strings ('true'/'false')
            if param == "nonStop":
                params[param] = str(flight_params[param]).lower()
            else:
                params[param] = flight_params[param]
    try:
        search_response = requests.get(search_url, headers=headers, params=params)
        search_response.raise_for_status()
        return search_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error searching for flight offers: {e}")
        return None

def get_flight_price(access_token, flight_offer):
    """
    Confirms the price and availability of a specific flight offer.
    """
    pricing_url = "https://test.api.amadeus.com/v1/shopping/flight-offers/pricing"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # The API expects the data to be wrapped in a specific structure
    request_body = {
        "data": {
            "type": "flight-offers-pricing",
            "flightOffers": [flight_offer]  # Pass the single flight offer in a list
        }
    }

    try:
        # We use json= instead of data= because we are sending a JSON body
        price_response = requests.post(pricing_url, headers=headers, json=request_body)
        price_response.raise_for_status()
        return price_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error confirming flight price: {e}")
        # It's often helpful to see the API's error message
        print(f"Response body: {e.response.text}")
        return None
    

def create_flight_order(access_token, priced_offer, travelers):
    """
    Creates a flight order (books a flight).
    """
    order_url = "https://test.api.amadeus.com/v1/booking/flight-orders"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # This is a simplified structure. A real-world application would need more details
    # like contact info, ticketing agreements, etc.
    request_body = {
        "data": {
            "type": "flight-order",
            "flightOffers": [priced_offer],
            "travelers": travelers
        }
    }

    try:
        order_response = requests.post(order_url, headers=headers, json=request_body)
        order_response.raise_for_status()
        return order_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating flight order: {e}")
        # Try to parse the JSON error response from the API and return it
        try:
            error_details = e.response.json()
            print(f"Response body: {error_details}")
            return error_details # Return the structured error
        except json.JSONDecodeError:
            # If the response isn't JSON, return a generic error structure
            print(f"Response body (not JSON): {e.response.text}")
            return {"errors": [{"detail": "An unknown error occurred during booking."}]}
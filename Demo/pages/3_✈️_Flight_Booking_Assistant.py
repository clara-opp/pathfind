import streamlit as st
import pandas as pd
import datetime
import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
import base64
import urllib.parse
import sqlite3
import time

# Import your API client modules
import amadeus_api_client as amadeus
import google_calendar_client as calendar_client

# --- Configuration and Initial Setup ---
load_dotenv()
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# This MUST match one of the "Authorized redirect URIs" in your Google Cloud Console
REDIRECT_URI = "http://localhost:8501/Flight_Booking_Assistant" 

# Initialize session state variables
if 'view_state' not in st.session_state:
    st.session_state.view_state = 'search' # 'search', 'results', 'booking', 'confirmation'
if 'flight_params' not in st.session_state:
    st.session_state.flight_params = {}
if 'flight_offers_data' not in st.session_state:
    st.session_state.flight_offers_data = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = pd.DataFrame() # Store the unfiltered, unsorted results
if 'display_df' not in st.session_state:
    st.session_state.display_df = pd.DataFrame() # The dataframe that is actually shown to the user
if 'priced_offer' not in st.session_state:
    st.session_state.priced_offer = None
if 'confirmed_booking' not in st.session_state:
    st.session_state.confirmed_booking = None
if 'google_creds' not in st.session_state:
    st.session_state.google_creds = None
if 'auth_state' not in st.session_state:
    st.session_state.auth_state = None
if 'iata_to_city' not in st.session_state:
    st.session_state.iata_to_city = {} # Store the airport code mapping
if 'iata_to_timezone' not in st.session_state:
    st.session_state.iata_to_timezone = {} # Store the timezone mapping
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'google_auth_flow_active' not in st.session_state:
    st.session_state.google_auth_flow_active = False
if 'search_mode' not in st.session_state:
    st.session_state.search_mode = 'manual' # 'manual' or 'chatbot'
 

# --- Helper Functions (migrated from main.py) ---

def extract_flight_info_with_gpt(conversation_history):
    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = f"""
    You are an intelligent flight search assistant. Your goal is to extract flight search parameters
    from a user's request into a specific JSON format. Ask clarifying questions ONLY when necessary. Today's date is {datetime.date.today().strftime('%Y-%m-%d')}.

    ## JSON Output Structure:
    - Your final output MUST be a JSON object.
    - Use `originLocationCode` and `destinationLocationCode` for airport codes.
    - Use `departureDate` for single dates, or `startDate` and `endDate` for ranges. Dates must be 'YYYY-MM-DD'.
    - Use `adults`, `children`, and `infants` for traveler counts.
    - If the user wants a direct flight, include `"nonStop": true`.

    ## Date Calculation Logic:
    - You are provided with today's date.
    - You MUST use this date to calculate the exact date for relative user requests (e.g., 'tomorrow', 'next Saturday', 'in 3 weeks').
    - If a date can be calculated, do not ask the user for clarification on the date. For example, if today is 2025-10-03 (a Friday) and the user says "next Saturday", you must calculate it as 2025-10-11.

    ## Traveler Age Rules:
    - 'children': Ages 2-11.
    - 'infants': Under 2 years old (traveling on an adult's lap).
    - 'adults': Ages 12 and up.

    ## Clarification Logic:
    - If the user does not specify the number of travelers, you MUST ask.
    - If a user mentions 'kids' or 'children' without specifying their ages, you MUST ask for their ages to correctly classify them.
    - Example: If the user says "flying with my wife and two kids", your response must be a JSON object containing:
      {{"followUpQuestion": "To ensure I find the right tickets, how old are your two children?"}}
    - Only include the `followUpQuestion` key if information is missing.
    - If all details are present, extract them into the specified JSON format and do not ask a question.
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    try:
        completion = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07", messages=messages, response_format={"type": "json_object"}
        )
        response_content = completion.choices[0].message.content
        # Basic parsing to handle potential markdown in the response
        if '```json' in response_content:
            json_str = response_content.split('```json\n')[1].split('```')
        else:
            json_str = response_content
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error processing your request with the AI model: {e}")
        return None

def extract_sorting_preference(user_query):
    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = """
    You are a data analysis assistant. Your task is to determine if a user's flight
    search query contains a preference for sorting the results.

    The results can be sorted by two columns:
    1. 'Price' (monetary value)
    2. 'Duration' (time length)

    - If the user mentions "cheapest", "lowest price", etc., they want to sort by 'Price' in ascending order.
    - If the user mentions "fastest", "quickest", "shortest", etc., they want to sort by 'Duration' in ascending order.

    Your output MUST be a JSON object with two keys: 'sort_by' and 'ascending'.
    - 'sort_by' must be either "Price" or "Duration".
    - 'ascending' will be true.

    If no preference is mentioned, return an empty JSON object `{}`.

    Example Query: "Find me the cheapest flight from JFK to LAX tomorrow."
    Example Response: {"sort_by": "Price", "ascending": true}
    """
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}]
    completion = client.chat.completions.create(model="gpt-5-nano-2025-08-07", messages=messages, response_format={"type": "json_object"})
    return json.loads(completion.choices[0].message.content)

def get_pandas_filter_code(user_query: str, df_columns: list) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = f"""
    You are an expert in Pandas DataFrames. Convert the user's query into a single line of Python code to filter a DataFrame named 'df'.
    The DataFrame has columns: {', '.join(df_columns)}.
    - For price, use 'Price' (numeric).
    - For airlines, use 'Carrier' (e.g., "United" -> df['Carrier'].str.contains('UNITED', case=False)).
    - For layovers, use 'Layovers' (numeric, e.g., "non-stop" -> df['Layovers'] == 0).
    - For sorting, use .sort_values(by='column'). For "cheapest", sort by 'Price'. For "fastest", sort by 'Duration'.
    - For "top 3", use .head(3).
    Respond ONLY with the Python code snippet.
    """
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}]
    completion = client.chat.completions.create(model="gpt-5-nano-2025-08-07", messages=messages)
    return completion.choices[0].message.content.strip()

def process_flight_offers_to_df(flight_offers_data):    
    # This function now relies on the session state being populated by populate_iata_mappings
    if not st.session_state.iata_to_city:
        if not populate_iata_mappings():
            return pd.DataFrame() # Return empty if DB connection fails

    carriers = flight_offers_data.get("dictionaries", {}).get("carriers", {})
    flight_params = st.session_state.flight_params
    flights = []
    for offer in flight_offers_data.get("data", []):
        if not offer.get("itineraries"): continue
        itinerary = offer["itineraries"][0]
        segments = itinerary.get("segments")
        if not segments: continue

        first_segment = segments[0]
        last_segment = segments[-1]
        num_layovers = len(segments) - 1

        # --- Process Layover Details (Structured) ---
        layovers_info = {}
        if num_layovers > 0:
            for i in range(num_layovers):
                layover_arrival = datetime.datetime.fromisoformat(segments[i]['arrival']['at'])
                layover_departure = datetime.datetime.fromisoformat(segments[i+1]['departure']['at'])
                layover_duration = layover_departure - layover_arrival
                layover_code = segments[i]['arrival']['iataCode']
                layover_name = st.session_state.iata_to_airport_name.get(layover_code, layover_code)
                layovers_info[layover_code] = {
                    "duration": layover_duration,
                    "airport_name": layover_name
                }

        # --- Parse total itinerary duration into timedelta for accurate sorting ---
        duration_raw = itinerary.get("duration", "PT0H0M")
        match = re.match(r'PT(\d+H)?(\d+M)?', duration_raw)
        hours, minutes = 0, 0
        if match:
            if match.group(1): hours = int(match.group(1)[:-1])
            if match.group(2): minutes = int(match.group(2)[:-1])
        total_duration_obj = datetime.timedelta(hours=hours, minutes=minutes)

        flights.append({
            "Origin": st.session_state.iata_to_city.get(first_segment['departure']['iataCode'], first_segment['departure']['iataCode']),
            "Destination": st.session_state.iata_to_city.get(last_segment['arrival']['iataCode'], last_segment['arrival']['iataCode']),
            "Departure": pd.to_datetime(first_segment['departure']['at']), # Keep as datetime object
            "Arrival": pd.to_datetime(last_segment['arrival']['at']),     # Keep as datetime object
            "Duration": total_duration_obj, # Keep as timedelta object
            "Carrier": carriers.get(first_segment["carrierCode"], "N/A"),
            "Layovers": num_layovers,
            "Layovers_Info": layovers_info, # dictionary
            "Segments": segments, # Add the full segments list for detailed display
            "Price": float(offer['price']['total']),
            "Currency": offer['price']['currency'],
            "Adults": flight_params.get("adults", 0),
            "Children": flight_params.get("children", 0),
            "Infants": flight_params.get("infants", 0)
        })
    df = pd.DataFrame(flights)
    # Format duration for display after calculations
    return df

def start_over():
    st.session_state.view_state = 'search'
    keys_to_clear = [k for k in st.session_state.keys() if k not in ['google_creds', 'view_state']]
    for key in keys_to_clear:
        del st.session_state[key]
    st.session_state.conversation_history = []

@st.cache_data
def get_airport_data_from_db():
    """Connects to the SQLite DB and fetches airport data. Caches the result."""
    conn = sqlite3.connect('airports.db')
    # Use a DataFrame for easier manipulation
    df = pd.read_sql_query("SELECT iata_code, name, city, timezone, page_rank FROM airports", conn)
    conn.close()
    return df

def populate_iata_mappings():
    """Reads the airport data from the DB and populates the IATA session state dicts."""
    try:
        airports_df = get_airport_data_from_db()
        airports_df.dropna(subset=['iata_code'], inplace=True)
        st.session_state.iata_to_city = airports_df.set_index('iata_code')['city'].to_dict()
        st.session_state.iata_to_airport_name = airports_df.set_index('iata_code')['name'].to_dict()
        st.session_state.iata_to_timezone = airports_df.set_index('iata_code')['timezone'].to_dict()
        return True
    except Exception as e:
        st.error(f"Error connecting to airports.db: {e}")
        return False
    
def search_flights(flight_params, initial_query=None):
    """Central function to search for flights and process results."""
    st.session_state.flight_params = flight_params
    access_token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
    if access_token:
        # --- Prepare for multi-airport and multi-date search ---
        origins = flight_params.get("originLocationCode", [])
        destinations = flight_params.get("destinationLocationCode", [])
        start_date_str = flight_params.get("departureDate")
        end_date_str = flight_params.get("endDate", start_date_str)

        # Ensure origins and destinations are lists
        if not isinstance(origins, list): origins = [origins]
        if not isinstance(destinations, list): destinations = [destinations]

        all_flight_offers_data = {"data": [], "dictionaries": {}}
        
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # --- Loop through all combinations ---
        num_days = (end_date - start_date).days + 1
        total_searches = len(origins) * len(destinations) * num_days
        if total_searches > 5:
            st.warning(f"This is a large search with {total_searches} combinations. It may take some time.")

        current_date = start_date
        while current_date <= end_date:
            for origin in origins:
                for destination in destinations:
                    if origin == destination: continue
                    
                    search_params = flight_params.copy()
                    search_params["originLocationCode"] = origin
                    search_params["destinationLocationCode"] = destination
                    search_params["departureDate"] = current_date.strftime("%Y-%m-%d")
                    
                    st.info(f"Searching: {origin} → {destination} on {current_date.strftime('%Y-%m-%d')}...")
                    daily_offers = amadeus.search_flight_offers(access_token, search_params)
                    if daily_offers and daily_offers.get("data"):
                        all_flight_offers_data["data"].extend(daily_offers["data"])
                        # Deep merge the dictionaries
                        for key, value_dict in daily_offers.get("dictionaries", {}).items():
                            all_flight_offers_data["dictionaries"].setdefault(key, {}).update(value_dict)
                    time.sleep(0.2) # Respect API rate limits
            current_date += datetime.timedelta(days=1)
        flight_offers = all_flight_offers_data
        if flight_offers and flight_offers.get("data"):
            st.session_state.flight_offers_data = flight_offers
            df = process_flight_offers_to_df(flight_offers)
            
            # Apply initial sorting preference if it was a chatbot query
            if initial_query:
                sorting_pref = extract_sorting_preference(initial_query)
                if sorting_pref and sorting_pref.get('sort_by') in df.columns:
                    df = df.sort_values(by=sorting_pref['sort_by'], ascending=sorting_pref.get('ascending', True))
            
            st.session_state.original_df = df
            st.session_state.display_df = df
            st.session_state.view_state = 'results'
            st.rerun()
        else:
            st.error("No flights found. Please try your search again.")
    else:
        st.error("Could not authenticate with Amadeus.")

def format_duration(td):
    """Formats a timedelta object into a more readable 'Xh Ym' string."""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"

# ====== Main App UI ======
st.title("✈️ Flight Booking Assistant")

# --- TOP-LEVEL HANDLER FOR GOOGLE OAUTH CALLBACK ---  
# This MUST run before the rest of the app's UI to correctly handle the redirect.
query_params = st.query_params
if "code" in query_params:
    st.info("DEBUG: Found 'code' in query_params. Handling Google callback.")
    # --- CRITICAL FIX: Repopulate the IATA mapping on callback ---
    populate_iata_mappings()
    st.write("DEBUG: Current query parameters:", query_params)
    with st.spinner("Finalizing calendar entry..."):
        # Decode the state from the URL to recover the priced_offer
        try:
            state_json_str = base64.urlsafe_b64decode(urllib.parse.unquote(query_params["state"])).decode('utf-8')
            recovered_state = json.loads(state_json_str)
            st.session_state.priced_offer = recovered_state.get("offer") # Restore the offer
            st.info("DEBUG: Successfully decoded state and recovered priced_offer.")
        except Exception as e:
            st.error(f"DEBUG: Failed to decode state from URL: {e}")
            st.session_state.priced_offer = None

        # Since we have recovered the state, we can proceed.
        # The state mismatch check is no longer relevant in this stateless approach.
        if st.session_state.priced_offer:
            flow = calendar_client.get_google_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
            st.session_state.google_creds = calendar_client.get_credentials_from_code(flow, query_params["state"], query_params["code"])
            st.write("DEBUG: Credentials object created:", st.session_state.google_creds)

            st.info("DEBUG: State matches. Fetching credentials.")

            service = calendar_client.get_calendar_service(st.session_state.google_creds)
            st.write("DEBUG: Priced offer available for calendar:", "Yes" if st.session_state.priced_offer else "No")
            if service and st.session_state.priced_offer:
                st.info("DEBUG: Service and priced_offer exist. Calling create_calendar_event.")
                itinerary = st.session_state.priced_offer['itineraries'][0]
                first_seg, last_seg = itinerary['segments'][0], itinerary['segments'][-1]
                origin_city = st.session_state.iata_to_city.get(first_seg['departure']['iataCode'])
                dest_city = st.session_state.iata_to_city.get(last_seg['arrival']['iataCode'])
                origin_tz = st.session_state.iata_to_timezone.get(first_seg['departure']['iataCode'], "UTC")
                dest_tz = st.session_state.iata_to_timezone.get(last_seg['arrival']['iataCode'], "UTC")
                summary = f"✈️ {origin_city} --> {dest_city}"
                
                calendar_client.create_calendar_event(
                    service, summary,
                    datetime.datetime.fromisoformat(first_seg['departure']['at']),
                    datetime.datetime.fromisoformat(last_seg['arrival']['at']),
                    origin_city, dest_city,
                    origin_tz, dest_tz
                )
            else:
                st.error("DEBUG: Could not create calendar event because service or priced_offer was missing.")
    
    # Clean up the URL and stop the auth flow
    st.query_params.clear()
    st.session_state.google_auth_flow_active = False # Explicitly turn it off
    # We don't rerun here, just let the script continue to the confirmation page view
 
# --- REDIRECT TO GOOGLE if the flag is set (e.g., by the button click) ---

# This is now separate from the callback handling.
if st.session_state.get("google_auth_flow_active"):
    st.markdown(f'<meta http-equiv="refresh" content="0; url={st.session_state.auth_url}">', unsafe_allow_html=True)
    st.stop()

# --- 1. SEARCH VIEW ---
if st.session_state.view_state == 'search':
    if st.session_state.search_mode == 'manual':
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header("Enter Flight Details")
        with col2:
            if st.button("🤖 Use Chatbot Instead"):
                st.session_state.search_mode = 'chatbot'
                st.rerun()
        # --- Manual Search Form ---
        try:
            airports_df = get_airport_data_from_db()
            airports_df.dropna(subset=['iata_code', 'city', 'name', 'page_rank'], inplace=True)
            airports_df.sort_values(by='page_rank', ascending=False, inplace=True)
            airports_df['display_name'] = airports_df['city'] + " (" + airports_df['iata_code'] + ") - " + airports_df['name']
            airport_options = airports_df['display_name'].tolist()
        except Exception as e:
            st.error(f"Could not load airport data from DB: {e}")
            airport_options = []
        with st.form("manual_search_form"):
            cols = st.columns(2)
            if airport_options:
                origin_display = cols[0].multiselect("Origin", options=airport_options, placeholder="Select one or more airports")
                destination_display = cols[1].multiselect("Destination", options=airport_options, placeholder="Select one or more airports")
            else:
                origin = cols[0].text_input("Origin (IATA Code)", "FRA")
                destination = cols[1].text_input("Destination (IATA Code)", "JFK")
            # A single date input component that handles both single date and date range selection
            today = datetime.date.today()
            next_week = today + datetime.timedelta(days=6)
            selected_dates = st.date_input(
                "Select Date or Date Range",
                (today, next_week),
                min_value=today
                )
            st.write("Travelers")
            cols = st.columns(3)
            adults = cols[0].number_input("Adults", min_value=1, value=1)
            children = cols[1].number_input("Children < 12 years", min_value=0, value=0)
            infants = cols[2].number_input("Infants < 2 years", min_value=0, value=0)
            non_stop = st.checkbox("Direct flights only", value=False)
            submitted = st.form_submit_button("Search Flights")
            if submitted:
                if not origin_display or not destination_display:
                    st.error("Please select at least one origin and one destination.")
                else:
                    # Process the output from the new date component
                    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                        start_date, end_date = selected_dates
                    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
                        start_date = end_date = selected_dates[0]
                    else: # Fallback for a single date object
                        start_date = end_date = selected_dates
                    origins = [re.search(r'\((\w{3})\)', o).group(1) for o in origin_display]
                    destinations = [re.search(r'\((\w{3})\)', d).group(1) for d in destination_display]
                    manual_params = {
                        "originLocationCode": origins,
                        "destinationLocationCode": destinations,
                        "departureDate": start_date.strftime("%Y-%m-%d"),
                        "endDate": end_date.strftime("%Y-%m-%d"),
                        "adults": adults, 
                        "children": children, 
                        "infants": infants,
                        "nonStop": non_stop
                    }
                    search_flights(manual_params)

    elif st.session_state.search_mode == 'chatbot':
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header("Describe Your Desired Flight")
        with col2:
            if st.button("📝 Use Manual Form"):
                st.session_state.search_mode = 'manual'
                st.rerun()
        # --- Chatbot Interface ---
        for message in st.session_state.conversation_history:
            with st.chat_message(message["role"]):
               st.markdown(message["content"])
        if user_query := st.chat_input("e.g., 'Flights from Frankfurt to New York tomorrow. One adult'"):
            st.session_state.conversation_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
            with st.spinner("Thinking..."):
                flight_params = extract_flight_info_with_gpt(st.session_state.conversation_history)
                if flight_params and "followUpQuestion" in flight_params:
                    question = flight_params['followUpQuestion']
                    st.session_state.conversation_history.append({"role": "assistant", "content": question})
                    with st.chat_message("assistant"):
                        st.markdown(question)
                elif flight_params:
                    with st.chat_message("assistant"):
                        st.markdown("Great, I have all the details. Searching for flights...")
                    search_flights(flight_params, user_query)

# --- 2. RESULTS VIEW ---
elif st.session_state.view_state == 'results':
    st.header("Flight Search Results")

    # --- Filtering UI ---
    with st.form("advanced_filter_form"):
        st.write("Filter and Sort Results")
        df_for_filters = st.session_state.original_df

        col1, col2, col3 = st.columns(3)
        with col1:
            min_price, max_price = st.slider(
                "Price Range (€)",
                min_value=int(df_for_filters['Price'].min()),
                max_value=int(df_for_filters['Price'].max()),
                value=(int(df_for_filters['Price'].min()), int(df_for_filters['Price'].max()))
            )
        with col2:
            max_duration_hours = st.slider(
                "Max Duration (hours)",
                min_value=int(df_for_filters['Duration'].min().total_seconds() / 3600),
                max_value=int(df_for_filters['Duration'].max().total_seconds() / 3600) + 1,
                value=int(df_for_filters['Duration'].max().total_seconds() / 3600) + 1
            )
        with col3:
            layover_options = sorted(df_for_filters['Layovers'].unique())
            selected_layovers = st.multiselect(
                "Number of Layovers", options=layover_options, default=layover_options
            )

        carrier_options = sorted(df_for_filters['Carrier'].unique())
        selected_carriers = st.multiselect(
            "Airlines", options=carrier_options, default=carrier_options
        )

        st.write("---")
        st.write("**Sorting Options**")
        sort_col1, sort_col2 = st.columns(2)
        with sort_col1:
            sort_by = st.selectbox("Sort by", options=['Price', 'Duration', 'Departure', 'Arrival', 'Layovers'])
        with sort_col2:
            sort_order = st.selectbox("Order", options=['Ascending', 'Descending'])

        col1, col2 = st.columns(2)
        with col1:
            start_time_range = st.slider(
                "Departure Time", value=(datetime.time(0, 0), datetime.time(23, 59)), format="HH:mm"
            )
        with col2:
            end_time_range = st.slider(
                "Arrival Time", value=(datetime.time(0, 0), datetime.time(23, 59)), format="HH:mm"
            )

        apply_filters_button = st.form_submit_button("Apply Filters & Sort")

    if apply_filters_button:
        filtered_df = st.session_state.original_df.copy()
        filtered_df = filtered_df[
            (filtered_df['Price'] >= min_price) &
            (filtered_df['Price'] <= max_price) &
            (filtered_df['Duration'] <= pd.to_timedelta(max_duration_hours, unit='h')) &
            (filtered_df['Layovers'].isin(selected_layovers)) &
            (filtered_df['Carrier'].isin(selected_carriers)) &
            (filtered_df['Departure'].dt.time >= start_time_range[0]) &
            (filtered_df['Departure'].dt.time <= start_time_range[1]) &
            (filtered_df['Arrival'].dt.time >= end_time_range[0]) &
            (filtered_df['Arrival'].dt.time <= end_time_range[1])
        ]
        ascending = (sort_order == 'Ascending')
        st.session_state.display_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
        st.rerun()

    if st.session_state.display_df.empty:
        st.warning("No flights match your current filter.")
    else:
        st.subheader(f"Displaying {len(st.session_state.display_df)} of {len(st.session_state.original_df)} flights")
        # Iterate over the DataFrame rows to create an expander for each flight
        for index, row in st.session_state.display_df.iterrows():
            duration_str = format_duration(row['Duration'])
            expander_title = f"✈️ {row['Origin']} to {row['Destination']} | **Duration:** {duration_str} | **Price:** €{row['Price']:.2f}"

            with st.expander(expander_title):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("**Flight Route & Timeline**")
                    segments = row['Segments']
                    st.markdown(f"**`{pd.to_datetime(segments[0]['departure']['at']).strftime('%H:%M')}`** departing from **{st.session_state.iata_to_city.get(segments[0]['departure']['iataCode'])}** ({segments[0]['departure']['iataCode']})")
                    if row['Layovers'] > 0:
                        for i, segment in enumerate(segments[:-1]):
                            layover_arrival_time = pd.to_datetime(segment['arrival']['at'])
                            layover_departure_time = pd.to_datetime(segments[i+1]['departure']['at'])
                            layover_duration = layover_departure_time - layover_arrival_time
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; &darr; *Flight duration: {format_duration(pd.to_timedelta(segment['duration']))}*")
                            st.markdown(f"**`{layover_arrival_time.strftime('%H:%M')}`** arrival at **{st.session_state.iata_to_city.get(segment['arrival']['iataCode'])}** ({segment['arrival']['iataCode']})")
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp; *Layover: {format_duration(layover_duration)}*")
                            st.markdown(f"**`{layover_departure_time.strftime('%H:%M')}`** departing from **{st.session_state.iata_to_city.get(segments[i+1]['departure']['iataCode'])}** ({segments[i+1]['departure']['iataCode']})")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; &darr; *Flight duration: {format_duration(pd.to_timedelta(segments[-1]['duration']))}*")
                    st.markdown(f"**`{pd.to_datetime(segments[-1]['arrival']['at']).strftime('%H:%M')}`** arrival at **{st.session_state.iata_to_city.get(segments[-1]['arrival']['iataCode'])}** ({segments[-1]['arrival']['iataCode']})")
                with col2:
                    st.markdown(f"**Carrier:**\n_{row['Carrier']}_")
                    if row['Layovers'] == 0:
                        st.markdown("**Layovers:**\n_Direct_")
                    else:
                        layover_str = "layover" if row['Layovers'] == 1 else "layovers"
                        st.markdown(f"**Layovers:**\n_{row['Layovers']} {layover_str}_")
                    if st.button("Confirm Price & Book", key=f"book_{index}"):
                        with st.spinner("Confirming price..."):
                            selected_offer = st.session_state.flight_offers_data['data'][index]
                            access_token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                            priced_offer_data = amadeus.get_flight_price(access_token, selected_offer)
                            if priced_offer_data:
                                st.session_state.priced_offer = priced_offer_data['data']['flightOffers'][0]
                                confirmed_price = float(st.session_state.priced_offer['price']['total'])
                                original_price = float(selected_offer['price']['total'])
                                if confirmed_price > original_price:
                                    st.warning(f"The price has increased from {original_price} to {confirmed_price}.")
                                st.session_state.view_state = 'booking'
                                st.rerun()
                            else:
                                st.error("Could not confirm price. Flight may be unavailable.")
    st.button("Start Over", on_click=start_over)

# --- 3. BOOKING VIEW ---
elif st.session_state.view_state == 'booking':
    st.header("Book Your Flight")
    price = st.session_state.priced_offer['price']
    st.subheader(f"Total Price: {price['total']} {price['currency']}")
    
    with st.form("traveler_form"):
        num_adults = st.session_state.flight_params.get("adults", 0)
        num_children = st.session_state.flight_params.get("children", 0)
        num_infants = st.session_state.flight_params.get("infants", 0)
        
        traveler_id_counter = 1

        # --- Generate forms for Adults ---
        for i in range(num_adults):
            st.subheader(f"Traveler {traveler_id_counter} (Adult)")
            cols = st.columns(2)
            cols[0].text_input("First Name", key=f"fn_{traveler_id_counter}")
            cols[1].text_input("Last Name", key=f"ln_{traveler_id_counter}")
            cols = st.columns(2)
            cols[0].date_input("Date of Birth", min_value=datetime.date(1920, 1, 1), key=f"dob_{traveler_id_counter}")
            cols[1].selectbox("Gender", ["MALE", "FEMALE"], key=f"g_{traveler_id_counter}")
            cols = st.columns(2)
            cols[0].text_input("Email Address", key=f"em_{traveler_id_counter}")
            cols[1].text_input("Phone Number", key=f"ph_{traveler_id_counter}")
            traveler_id_counter += 1

        # --- Generate forms for Children ---
        for i in range(num_children):
            st.subheader(f"Traveler {traveler_id_counter} (Child)")
            cols = st.columns(2)
            cols[0].text_input("First Name", key=f"fn_{traveler_id_counter}")
            cols[1].text_input("Last Name", key=f"ln_{traveler_id_counter}")
            cols = st.columns(2)
            cols[0].date_input("Date of Birth", min_value=datetime.date(2010, 1, 1), key=f"dob_{traveler_id_counter}")
            cols[1].selectbox("Gender", ["MALE", "FEMALE"], key=f"g_{traveler_id_counter}")
            traveler_id_counter += 1

        # --- Generate forms for Infants ---
        for i in range(num_infants):
            st.subheader(f"Traveler {traveler_id_counter} (Infant)")
            cols = st.columns(2)
            cols[0].text_input("First Name", key=f"fn_{traveler_id_counter}")
            cols[1].text_input("Last Name", key=f"ln_{traveler_id_counter}")
            cols = st.columns(2)
            cols[0].date_input("Date of Birth", min_value=datetime.date(2023, 1, 1), key=f"dob_{traveler_id_counter}")
            cols[1].selectbox("Gender", ["MALE", "FEMALE"], key=f"g_{traveler_id_counter}")
            traveler_id_counter += 1
        
        submitted = st.form_submit_button("Confirm and Book Flight")

    if submitted:
        travelers = []
        total_travelers = num_adults + num_children + num_infants
        for i in range(1, total_travelers + 1):
            # For simplicity, we'll associate the contact info of the first traveler with all travelers
            email = st.session_state.get(f"em_{i}", st.session_state.get("em_1", ""))
            phone = st.session_state.get(f"ph_{i}", st.session_state.get("ph_1", ""))
            travelers.append({
                "id": str(i), "dateOfBirth": st.session_state[f"dob_{i}"].strftime("%Y-%m-%d"),
                "name": {"firstName": st.session_state[f"fn_{i}"], "lastName": st.session_state[f"ln_{i}"]},
                "gender": st.session_state[f"g_{i}"],
                "contact": {"emailAddress": email, "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": phone}]}
            })
        
        with st.spinner("Booking your flight..."):
            access_token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
            order = amadeus.create_flight_order(access_token, st.session_state.priced_offer, travelers)
            if 'data' in order:
                st.session_state.confirmed_booking = order
                st.session_state.view_state = 'confirmation'
                st.rerun()
            elif 'errors' in order:
                # We have a structured error from the API
                error_messages = []
                for error in order['errors']:
                    detail = error.get('detail', 'An unspecified error occurred.')
                    source_pointer = error.get('source', {}).get('pointer', '')

                    # Try to map the error source back to a user-friendly field name
                    field_name = "in the form" # Default
                    traveler_index = -1

                    if source_pointer:
                        match = re.search(r'/travelers/(\d+)', source_pointer)
                        if match:
                            traveler_index = int(match.group(1)) + 1
                    
                    # Make the error message more specific
                    if "dateOfBirth" in source_pointer:
                        field_name = "Date of Birth"
                    elif "firstName" in source_pointer:
                        field_name = "First Name"

                    if traveler_index != -1:
                        error_messages.append(f"Error for Traveler {traveler_index} (Field: {field_name}): {detail}")
                    else:
                        error_messages.append(f"Booking Error: {detail}")

                # Display all formatted error messages
                for msg in error_messages:
                    st.error(msg)
            else:
                st.error("Booking failed. An unknown error occurred. Please try again.")
             
    st.button("Back to Results", on_click=lambda: st.session_state.update(view_state='results'))

# --- 4. CONFIRMATION VIEW & GOOGLE CALENDAR ---
elif st.session_state.view_state == 'confirmation':
    st.header("🎉 Booking Successful!")
    pnr = st.session_state.confirmed_booking['data']['associatedRecords'][0]['reference']
    st.success(f"Your booking is confirmed! Your reference (PNR) is: **{pnr}**")

    st.subheader("Add to Google Calendar")
    if st.session_state.google_creds:
        # If we have credentials, the top-level handler has already run.
        # We can just show a success message.
        st.success("✅ Flight event has been added to your Google Calendar!")
    else:
        # Generate the auth URL once and store it.
        if 'auth_url' not in st.session_state or st.session_state.auth_url is None:
            flow = calendar_client.get_google_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
            # Create a composite state that includes the flight offer data
            state_to_encode = {
                "offer": st.session_state.priced_offer,
                # In a production app, you would add a CSRF token here as well
            }
            state_json_str = json.dumps(state_to_encode)
            # Use Base64 for robust encoding that is URL-safe
            encoded_state = base64.urlsafe_b64encode(state_json_str.encode('utf-8')).decode('utf-8')

            auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=encoded_state)
            st.session_state.auth_url = auth_url
        
        # This button's ONLY job is to set the flag and trigger a rerun.
        if st.button("Log in with Google to add to calendar"):
            st.session_state.google_auth_flow_active = True
            st.rerun()

    st.button("Book Another Flight", on_click=start_over)
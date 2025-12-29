import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import random
import datetime
import time
import os
import json
import re
import base64
import urllib.parse
from dotenv import load_dotenv
from openai import OpenAI
import amadeus_api_client as amadeus
import google_calendar_client as calendar_client
import requests

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
load_dotenv()
st.set_page_config(
    page_title="Global Travel Planner",
    page_icon="🌏",
    layout="wide",
)

# API Keys
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8501" 

@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

client = get_openai_client()

# Custom CSS for styling - Clean & Overlap-free
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        
        /* Global Font - Target specific elements to avoid breaking icons */
        html, body, .stMarkdown, div[data-testid="stText"], .stButton button { 
            font-family: 'Poppins', sans-serif !important; 
            color: var(--text-color);
        }
        
        /* Headers */
        .main-header { 
            font-size: 3rem; 
            color: #1a237e; 
            font-weight: 700; 
            text-align: center; 
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .sub-header { 
            text-align: center; 
            color: #666; 
            font-size: 1.2rem;
            margin-bottom: 3rem; 
        }

        @media (prefers-color-scheme: dark) {
            .main-header {
            color: #2949FF; 
            }
            .sub-header {
            color: #A1A1A1; 
            }
        }
        
        /* Cards */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
        }

        /* Flight Result Styling */
        .price-text { color: var(--primary-color); font-size: 1.4rem; font-weight: 700; }
        .carrier-text { font-size: 1.1rem; font-weight: 600; color: var(--text-color); }
        .route-text { color: var(--text-color); opacity: 0.7; font-size: 0.9rem; }
        
        /* Timeline Styling */
        .time-badge { background-color: #1e1e1e; color: #4caf50; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-weight: 700; margin-right: 10px; border: 1px solid #4caf50; }
        .timeline-row { margin: 2px 0; display: flex; align-items: center; font-size: 0.9rem; }
        .duration-info { margin-left: 35px; color: var(--text-color); opacity: 0.6; font-style: italic; font-size: 0.8rem; }
        .layover-info { margin: 5px 0; text-align: left; padding-left: 50px; color: var(--text-color); opacity: 0.8; font-style: italic; font-size: 0.85rem; border-top: 1px dashed var(--text-color); border-bottom: 1px dashed var(--text-color); padding: 2px 0 2px 50px; }
        .city-name { font-weight: 700; color: var(--text-color); }
        .iata-code { color: var(--text-color); opacity: 0.6; }
        
        /* Swiping Cards */
        .swipe-card { 
            text-align: center; 
            padding: 2rem; 
            border: 2px dashed #e0e0e0; 
            border-radius: 15px; 
            background-color: #fafafa;
        }
        .swipe-card h3 { color: #333; margin-bottom: 2rem; }
        .swipe-icon { font-size: 4rem; display: block; margin-bottom: 1rem; }
        
        /* Buttons */
        .stButton>button { 
            width: 100%; 
            border-radius: 8px; 
            height: 3em;
            font-weight: 600; 
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        /* Primary Button Style override */
        div[data-testid="stButton"] > button {
            background-color: #1a237e;
            color: white;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #283593;
            color: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LAYER (Model)
# ==========================================
class DataManager:
    def __init__(self, db_name='unified_country_database.db'):
        self.db_path = self._find_db(db_name)

    def _find_db(self, db_name):
        current_dir = Path(__file__).parent
        paths = [current_dir / db_name, current_dir / "data" / db_name]
        for path in paths:
            if path.exists():
                return str(path)
        st.error(f"🚨 Database '{db_name}' not found!"); return None

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    @st.cache_data
    def load_base_data(_self, origin_iata):
        query = """
        WITH MajorAirports AS (
            SELECT iso2, iata_code
            FROM (
                SELECT iso2, iata_code, 
                       ROW_NUMBER() OVER (PARTITION BY iso2 ORDER BY passenger_volume DESC) as rank
                FROM airports
            ) WHERE rank = 1
        )
        SELECT 
            c.iso2, c.iso3, c.country_name, c.tugo_advisory_state, c.pli_ppp,
            c.img_1, c.img_2, c.img_3,
            cm.climate_avg_temp_c,
            (SELECT COUNT(*) FROM unesco_heritage_sites u WHERE u.country_iso = c.iso2) as unesco_count,
            fc.price_eur as flight_price,
            fc.origin as flight_origin,
            fc.destination as flight_dest
        FROM countries c 
        LEFT JOIN climate_monthly cm ON c.country_name = cm.country_name_climate
        LEFT JOIN MajorAirports ma ON c.iso2 = ma.iso2
        LEFT JOIN flight_costs fc ON ma.iata_code = fc.destination AND fc.origin = ?
          """
        conn = _self.get_connection()
        df = pd.read_sql(query, conn, params=(origin_iata,))
        conn.close()
        return df

    @st.cache_data
    def get_country_details(_self, iso2):
        conn = _self.get_connection()
        details = {
            'safety': pd.read_sql("SELECT category, description FROM tugo_safety WHERE iso2 = ?", conn, params=(iso2,)),
            'health': pd.read_sql("SELECT disease_name, description FROM tugo_health WHERE iso2 = ? LIMIT 5", conn, params=(iso2,)),
            'entry': pd.read_sql("SELECT category, description FROM tugo_entry WHERE iso2 = ?", conn, params=(iso2,)),
            'unesco': pd.read_sql("SELECT name, category FROM unesco_heritage_sites WHERE country_iso = ? LIMIT 10", conn, params=(iso2,)),
        }
        conn.close()
        return details
        
    @st.cache_data
    def get_airports(_self, iso2=None):
        conn = sqlite3.connect(_self.db_path)
        if iso2:
            query = "SELECT iata_code, city, name FROM airports WHERE iso2 = ? ORDER BY passenger_volume DESC"
            df = pd.read_sql(query, conn, params=(iso2,))
        else:
            query = "SELECT iata_code, city, name FROM airports ORDER BY passenger_volume DESC LIMIT 500"
            df = pd.read_sql(query, conn)
        conn.close()
        df['display'] = df['city'] + " (" + df['iata_code'] + ")"
        return df

    @st.cache_data
    def get_iata_mappings(_self):
            conn = _self.get_connection()
            df = pd.read_sql("SELECT iata_code, city, name, timezone FROM airports", conn)
            conn.close()
            return {
                'city': df.set_index('iata_code')['city'].to_dict(),
                'name': df.set_index('iata_code')['name'].to_dict(),
                'tz': df.set_index('iata_code')['timezone'].to_dict()
            }
    
    @st.cache_data
    def get_exchange_rate(_self, currency_code):
        conn = _self.get_connection()
        query = "SELECT one_eur_to_currency FROM numbeo_exchange_rates WHERE currency = ?"
        res = pd.read_sql(query, conn, params=(currency_code,))
        conn.close()
        return res.iloc[0]['one_eur_to_currency'] if not res.empty else 1.0

data_manager = DataManager()

# ==========================================
# 3. LOGIC LAYER (Controller)
# ==========================================
class TravelMatcher:
    def __init__(self, df): self.df = df.copy()
    def normalize(self, series): return (series - series.min()) / (series.max() - series.min())
    def calculate_match(self, weights, prefs):
        df = self.df.copy()
        # Safety Score
        df['safety_score'] = df['tugo_advisory_state'].apply(lambda x: 0.1 if 'Do not travel' in str(x) else (0.4 if 'high degree' in str(x) else 0.9))
        # Budget Score (lower PLI is better)
        df['pli_ppp'] = pd.to_numeric(df['pli_ppp'], errors='coerce').fillna(100)
        df['budget_score'] = 1 - self.normalize(df['pli_ppp'])
        # Weather Score
        target_temp = prefs.get('target_temp', 25)
        df['climate_avg_temp_c'] = pd.to_numeric(df['climate_avg_temp_c'], errors='coerce').fillna(target_temp)
        df['weather_score'] = 1 - self.normalize(abs(df['climate_avg_temp_c'] - target_temp))
        # Culture Score
        df['unesco_count'] = df['unesco_count'].fillna(0)
        df['culture_score'] = self.normalize(df['unesco_count'])
        # Astro Score
        if weights.get('astro', 0) > 0:
            df['astro_score'] = df['country_name'].apply(lambda c: random.random())
        else:
            df['astro_score'] = 0
        # Final Score
        df['final_score'] = (
            df['safety_score'] * weights['safety'] + df['budget_score'] * weights['budget'] +
            df['weather_score'] * weights['weather'] + df['culture_score'] * weights['culture'] +
            df['astro_score'] * weights.get('astro', 0)
        )
        return df.sort_values('final_score', ascending=False).reset_index(drop=True)
    
def extract_flight_info_with_gpt(conversation_history):
    system_prompt = f"""
    You are an intelligent flight search assistant. Your goal is to extract flight search parameters
    from a user's request into a specific JSON format. Ask clarifying questions ONLY when necessary. Today's date is {datetime.date.today().strftime('%Y-%m-%d')}.

    ## JSON Output Structure:
    - Your final output MUST be a JSON object.
    - Use `originLocationCode` and `destinationLocationCode` for airport codes.
    - Use `departureDate` for single dates, or `startDate` and `endDate` for ranges. Dates must be 'YYYY-MM-DD'.
    - Use `adults`, `children`, and `infants` for traveler counts.
    - If the user wants a direct flight, include `"nonStop": true`.
    - For travel class, use `travelClass` with one of the following values: "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST". Default to "ECONOMY" if not specified.
    
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

def format_duration(duration_str):
    if isinstance(duration_str, datetime.timedelta):
        total_seconds = int(duration_str.total_seconds())
        return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    match = re.match(r'PT(\d+H)?(\d+M)?', duration_str)
    h = match.group(1)[:-1] if match.group(1) else "0"
    m = match.group(2)[:-1] if match.group(2) else "0"
    return f"{h}h {m}m"

def parse_duration_to_td(duration_raw):
    match = re.match(r'PT(\d+H)?(\d+M)?', duration_raw)
    h, m = 0, 0
    if match:
        if match.group(1): h = int(match.group(1)[:-1])
        if match.group(2): m = int(match.group(2)[:-1])
    return datetime.timedelta(hours=h, minutes=m)

# ==========================================
# 4. VIEW LAYER (UI Steps)
# ==========================================
SWIPE_CARDS = [
    {"id": "weather", "title": "What's the vibe?", "left": {"label": "Beach & Sun", "icon": "☀️"}, "right": {"label": "Cozy & Cool", "icon": "🧥"}},
    {"id": "budget", "title": "How are we spending?", "left": {"label": "Luxury Escape", "icon": "💎"}, "right": {"label": "Budget Adventure", "icon": "💰"}},
    {"id": "culture", "title": "What will we explore?", "left": {"label": "History & Museums", "icon": "🏛️"}, "right": {"label": "Nature & Parks", "icon": "🌳"}},
    {"id": "pace", "title": "What's the pace?", "left": {"label": "Action-Packed", "icon": "⚡"}, "right": {"label": "Relax & Unwind", "icon": "🧘"}},
]

def show_profile_step():
    st.markdown("### Step 1: 📍 Where are you starting from?")
    origin_options = {"Germany": "FRA", "United States": "ATL"}
    selected_origin = st.radio("Select origin:", list(origin_options.keys()), horizontal=True, label_visibility="collapsed")
    st.session_state.origin_iata = origin_options[selected_origin]
    st.markdown("### Step 2: 🧭 Choose Your Traveller Profile")
    st.write("Select a profile to start with a set of curated preferences. You can fine-tune them with swiping cards in the next step!")
    
    personas = {
        "🗺️ Adventurous Solo": {'safety': 0.3, 'budget': 0.8, 'weather': 0.4, 'culture': 0.7},
        "👨‍👩‍👧‍👦 Family Vacation": {'safety': 1.0, 'budget': 0.4, 'weather': 0.7, 'culture': 0.4},
        "💻 Digital Nomad": {'safety': 0.7, 'budget': 1.0, 'weather': 0.5, 'culture': 0.2},
        "❤️ Honeymoon Luxury": {'safety': 0.8, 'budget': 0.2, 'weather': 0.9, 'culture': 0.6},
    }
    
    col1, _ = st.columns([2, 1])
    with col1:
        persona = st.selectbox("Select a persona:", list(personas.keys()), label_visibility="collapsed")
    
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True) 

    if st.button("Next: Personalize Your Trip →"):
        st.session_state.weights = personas[persona]
        st.session_state.prefs = {'target_temp': 25} 

        # Initialize estimation currency based on origin
        if st.session_state.origin_iata == "ATL":
            st.session_state.currency_symbol = "$"
            st.session_state.currency_rate = data_manager.get_exchange_rate("USD")
        else:
            st.session_state.currency_symbol = "€"
            st.session_state.currency_rate = 1.0

        st.session_state.step = 2
        st.rerun()

    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True) 

    with st.expander("Advanced Customization (Optional)"):
        st.write("Tweaking these will override the default persona weights.")
        st.slider("Safety Importance", 0.0, 1.0, 0.5, key="adv_safety")
        st.slider("Budget Importance (Low Cost)", 0.0, 1.0, 0.5, key="adv_budget")

def show_swiping_step():
    # --- FIX: Check if we are done BEFORE trying to render a card ---
    if st.session_state.card_index >= len(SWIPE_CARDS):
        st.session_state.step = 3
        st.rerun()
        return

    card_index = st.session_state.card_index
    # Ensure progress is always between 0.0 and 1.0
    progress_val = min((card_index + 1) / len(SWIPE_CARDS), 1.0)
    
    st.markdown(f"### Step 3: Swipe to Refine Your Choices ({card_index + 1}/{len(SWIPE_CARDS)})")
    st.progress(progress_val)
    
    card = SWIPE_CARDS[card_index]
    
    with st.container():
        st.markdown(f"<div class='card swipe-card'><h3>{card['title']}</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown(f"<span class='swipe-icon'>{card['left']['icon']}</span>", unsafe_allow_html=True)
            if st.button(card['left']['label'], key=f"left_{card_index}"):
                if card['id'] == 'weather': st.session_state.prefs['target_temp'] = 28
                if card['id'] == 'budget': st.session_state.weights['budget'] *= 0.7
                if card['id'] == 'culture': st.session_state.weights['culture'] *= 1.3
                if card['id'] == 'pace': st.session_state.weights['safety'] *= 0.8
                st.session_state.card_index += 1
                st.rerun()

        with c2:
            st.markdown(f"<span class='swipe-icon'>{card['right']['icon']}</span>", unsafe_allow_html=True)
            if st.button(card['right']['label'], key=f"right_{card_index}"):
                if card['id'] == 'weather': st.session_state.prefs['target_temp'] = 18
                if card['id'] == 'budget': st.session_state.weights['budget'] *= 1.3
                if card['id'] == 'culture': st.session_state.weights['culture'] *= 0.7
                if card['id'] == 'pace': st.session_state.weights['safety'] *= 1.2
                st.session_state.card_index += 1
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def show_astro_step():
    st.markdown("### Step 4: A Final Touch of Destiny? ✨")
    
    st.markdown("#### 🃏 Draw Your Mystical Travel Card")
    
    if st.button("Draw Tarot Card", use_container_width=True, key="draw_tarot"):
        try:
            # API Call für Tarot-Karte
            api_key = os.getenv("ROXY_API_KEY")
            tarot_url = "https://roxyapi.com/api/v1/data/astro/tarot"
            url = f"{tarot_url}/single-card-draw?token={api_key}&reversed_probability=0.3"
            
            response = requests.get(url)
            
            if response.status_code == 200:
                card_data = response.json()
                card_name = card_data.get("name", "Unknown Card")
                is_reversed = card_data.get("is_reversed", False)
                card_image = card_data.get("image", "")
                
                # Länder aus Datenbank holen
                conn = sqlite3.connect("unified_country_database.db")
                cursor = conn.cursor()
                
                orientation = "reversed" if is_reversed else "upright"
                cursor.execute("""
                    SELECT DISTINCT country_code, country_name, reason 
                    FROM tarot_countries 
                    WHERE card_name = ? AND orientation = ?
                """, (card_name, orientation))
                
                results = cursor.fetchall()
                conn.close()
                
                if results:
                    # Länder speichern
                    tarot_countries = [row[0] for row in results]
                    st.session_state["tarot_countries"] = tarot_countries
                    st.session_state["weights"]["astro"] = 0.2
                    
                    # UI: Karte anzeigen
                    orientation_text = "🔄 Reversed" if is_reversed else "⬆️ Upright"
                    st.success(f"✨ **{card_name}** ({orientation_text})")
                    
                    if card_image:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(card_image, width=200)
                    
                    # Empfohlene Länder anzeigen
                    st.markdown("#### 🌍 Recommended Destinations:")
                    for country_code, country_name, reason in results:
                        st.write(f"**{country_name}** ({country_code})")
                        st.caption(f"_{reason}_")
                else:
                    st.warning(f"Card '{card_name}' found but no countries in tarot database.")
                    st.session_state["tarot_countries"] = []
            else:
                st.error(f"API Error: {response.status_code}")
                
        except Exception as e:
            st.error(f"Error drawing tarot card: {str(e)}")
    
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    if st.button("Calculate My Matches! 🚀", use_container_width=True):
        st.session_state.step = 4
        st.rerun()


def show_results_step():
    st.markdown("### Step 5: Your Top Destinations!")
    with st.spinner("Analyzing the globe to find your perfect spot..."):
        df_base = data_manager.load_base_data(st.session_state.get('origin_iata', 'FRA'))
        matcher = TravelMatcher(df_base)
        st.session_state.matched_df = matcher.calculate_match(st.session_state.weights, st.session_state.prefs)

    df = st.session_state.matched_df
    top_5 = df.head(5)
    
    st.balloons()
    st.success(f"**Your #1 Match: {top_5.iloc[0]['country_name']}**")
    
    for i, row in top_5.iterrows():
        with st.container():
            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 2, 1])
            with c1:
                img_url = row[random.choice(['img_1', 'img_2', 'img_3'])]
                if img_url:
                    st.image(img_url, use_container_width=True)
            with c2:
                st.markdown(f"#### {i+1}. {row['country_name']}")
                score = row['final_score'] / sum(st.session_state.weights.values()) * 100
                st.markdown(f"**Match Score:** <span style='color:green; font-weight:bold'>{score:.0f}%</span>", unsafe_allow_html=True)
                if pd.notnull(row['flight_price']):
                    # Convert database EUR estimate to local currency
                    rate = st.session_state.get('currency_rate', 1.0)
                    symbol = st.session_state.get('currency_symbol', '€')
                    converted_price = row['flight_price'] * rate
                    tooltip = f"Two-way flight from {row['flight_origin']} to {row['flight_dest']}"
                    st.markdown(f"✈️ Est. Flight: **{symbol}{converted_price:.0f}**", help=tooltip)
            with c3:
                if st.button("View Details", key=f"details_{row['iso2']}"):
                    st.session_state.selected_country = row
                    st.session_state.step = 5
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()

def show_dashboard_step():
    country = st.session_state.selected_country
    st.markdown(f"### 📋 Dashboard: {country['country_name']}")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛡️ Safety", "🏥 Health & Visa", "🏛️ Culture", "💰 Budget", "✈️ Find Flights"])
    
    details = data_manager.get_country_details(country['iso2'])
    with tab1: 
        st.info(f"Advisory: {country['tugo_advisory_state']}")
        if not details['safety'].empty: st.dataframe(details['safety'], use_container_width=True)
    with tab2:
        st.write("#### Vaccinations & Diseases"); st.dataframe(details['health'], use_container_width=True)
    with tab3:
        st.metric("UNESCO World Heritage Sites", country['unesco_count'])
        if not details['unesco'].empty: st.dataframe(details['unesco'], use_container_width=True)
    with tab4:
        st.metric("Price Level Index (Lower is Cheaper)", f"{country['pli_ppp']:.2f}")
    with tab5:
        mode = st.radio("Search Mode", ["Manual Search", "AI Flight Chatbot"], horizontal=True)
        all_airports = data_manager.get_airports()
        dest_airports = data_manager.get_airports(country['iso2'])
        
        if mode == "Manual Search":
            c1, col2, col3 = st.columns(3)
            default_origin = st.session_state.get('origin_iata', 'FRA')
            origin_index = all_airports[all_airports['iata_code'] == default_origin].index[0] if not all_airports[all_airports['iata_code'] == default_origin].empty else 0
            orig = c1.selectbox("Flying from:", all_airports['display'], index=int(origin_index))
            dest = col2.selectbox("Flying to:", dest_airports['display'])
            dates = col3.date_input("Dates:", [datetime.date.today() + datetime.timedelta(days=14), datetime.date.today() + datetime.timedelta(days=17)])

            c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1])
            t_class = c4.selectbox("Class", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
            ad = c5.number_input("Adults (12y+)", 1, 9, 1)
            ch = c6.number_input("Children (2-11y)", 0, 9, 0)
            inf = c7.number_input("Infants (<2y)", 0, 9, 0)
            # Save counts for the booking step
            st.session_state.traveler_counts = {"ADULT": ad, "CHILD": ch, "INFANT": inf}
            non_stop = c8.checkbox("Non-stop")

            if st.button("Search Flights 🚀", use_container_width=True, key="manual_search_btn"):
                imgs = [country.get('img_1'), country.get('img_2'), country.get('img_3')]
                imgs = [img for img in imgs if img]
                img_placeholder = st.empty()
                if isinstance(dates, (list, tuple)):
                    start_d = dates[0]
                    end_d = dates[1] if len(dates) > 1 else start_d
                else:
                    start_d = end_d = dates
                token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                all_res = {"data": [], "dictionaries": {"carriers": {}}}
                curr = start_d
                img_idx = 0
                last_img_time = 0
                while curr <= end_d:
                    if imgs and (time.time() - last_img_time > 5.0):
                        img_url = imgs[img_idx % len(imgs)]
                        u_id = int(time.time() * 1000)
                        img_placeholder.markdown(f"""
                            <style>
                                @keyframes fadeIO_{u_id} {{ 
                                    0% {{ opacity: 0; }} 
                                    15% {{ opacity: 1; }} 
                                    85% {{ opacity: 1; }} 
                                    100% {{ opacity: 0; }} 
                                }}
                                .fade_{u_id} {{ animation: fadeIO_{u_id} 6s ease-in-out forwards;
                                }}
                            </style>
                            <div class="fade_{u_id}">
                                <img src="{img_url}" style="width:100%; border-radius:12px;">
                                <p style="text-align:center; color:gray; font-style:italic;">Searching for flights on {curr}...</p>
                            </div>
                        """, unsafe_allow_html=True)
                        img_idx += 1
                        last_img_time = time.time()
                    params = {
                        "originLocationCode": orig[-4:-1], 
                        "destinationLocationCode": dest[-4:-1], 
                        "departureDate": curr.strftime("%Y-%m-%d"), 
                        "adults": ad,
                        "children": ch,
                        "infants": inf,
                        "travelClass": t_class, 
                        "nonStop": non_stop,
                        "currencyCode": "USD" if st.session_state.origin_iata == "ATL" else "EUR"
                    }
                    res = amadeus.search_flight_offers(token, params)
                    if res.get('data'):
                        all_res['data'].extend(res['data'])
                        all_res['dictionaries']['carriers'].update(res.get('dictionaries', {}).get('carriers', {}))
                    time.sleep(0.1) # Prevent API Rate Limiting
                    curr += datetime.timedelta(days=1)
                img_placeholder.empty()
                st.session_state.flight_results = all_res
        else:
            if prompt := st.chat_input("Flights from Berlin next Tuesday"):
                st.session_state.conversation.append({"role": "user", "content": prompt})
                with st.spinner("AI is analyzing your request..."):
                    params = extract_flight_info_with_gpt(st.session_state.conversation)
                    if "followUpQuestion" in params:
                        st.session_state.conversation.append({"role": "assistant", "content": params["followUpQuestion"]})
                        st.rerun()

                    # Sync AI-extracted traveler counts to session state for the booking form
                    st.session_state.traveler_counts = {
                        "ADULT": params.get("adults", 1),
                        "CHILD": params.get("children", 0),
                        "INFANT": params.get("infants", 0)
                    }
                    
                    imgs = [country.get('img_1'), country.get('img_2'), country.get('img_3')]
                    imgs = [img for img in imgs if img]
                    img_placeholder = st.empty()

                    token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                    params["destinationLocationCode"] = dest_airports.iloc[0]['iata_code']
                    params["currencyCode"] = "USD" if st.session_state.origin_iata == "ATL" else "EUR"
                    start_d = datetime.datetime.strptime(params.get('departureDate') or params.get('startDate'), "%Y-%m-%d").date()
                    end_d = datetime.datetime.strptime(params.get('endDate', start_d.strftime("%Y-%m-%d")), "%Y-%m-%d").date()
                    all_res = {"data": [], "dictionaries": {"carriers": {}}}
                    curr = start_d
                    img_idx = 0
                    last_img_time = 0
                    while curr <= end_d:
                        if imgs and (time.time() - last_img_time > 5.0):
                            img_url = imgs[img_idx % len(imgs)]
                            u_id = int(time.time() * 1000)
                            img_placeholder.markdown(f"""
                                <style>
                                    @keyframes fadeIO_{u_id} {{ 
                                        0% {{ opacity: 0; }} 
                                        15% {{ opacity: 1; }} 
                                        85% {{ opacity: 1; }} 
                                        100% {{ opacity: 0; }} 
                                    }}
                                    .fade_{u_id} {{ animation: fadeIO_{u_id} 6s ease-in-out forwards; 
                                    }}
                                </style>
                                <div class="fade_{u_id}">
                                    <img src="{img_url}" style="width:100%; border-radius:12px;">
                                    <p style="text-align:center; color:gray; font-style:italic;">AI is checking {curr}...</p>
                                </div>
                            """, unsafe_allow_html=True)
                            img_idx += 1
                            last_img_time = time.time()
                        params['departureDate'] = curr.strftime("%Y-%m-%d")
                        res = amadeus.search_flight_offers(token, params)
                        if res.get('data'):
                            all_res['data'].extend(res['data'])
                            all_res['dictionaries']['carriers'].update(res.get('dictionaries', {}).get('carriers', {}))
                        time.sleep(0.1) # Prevent API Rate Limiting
                        curr += datetime.timedelta(days=1)
                    img_placeholder.empty()
                    st.session_state.flight_results = all_res

        if st.session_state.get('flight_results') and st.session_state.flight_results.get('data'):
            maps = data_manager.get_iata_mappings()
            carriers = st.session_state.flight_results['dictionaries']['carriers']
            
            # Process to DF for filtering/sorting
            processed_data = []
            for idx, offer in enumerate(st.session_state.flight_results['data']):
                itinerary = offer['itineraries'][0]
                processed_data.append({
                    'idx': idx,
                    'Price': float(offer['price']['total']),
                    'Currency': offer['price']['currency'],
                    'Duration': parse_duration_to_td(itinerary['duration']),
                    'Carrier': carriers.get(itinerary['segments'][0]['carrierCode'], "N/A"),
                    'Layovers': len(itinerary['segments']) - 1,
                    'Departure': pd.to_datetime(itinerary['segments'][0]['departure']['at'])
                })
            df = pd.DataFrame(processed_data)

            with st.expander("Filters & Sorting"):
                f_col1, f_col2 = st.columns(2)
                max_p = f_col1.slider("Price", float(df['Price'].min()), float(df['Price'].max()), float(df['Price'].max()))
                max_dur = f_col1.slider("Duration (Hours)", 1, int(df['Duration'].dt.total_seconds().max() / 3600) + 1, int(df['Duration'].dt.total_seconds().max() / 3600) + 1)
                max_lay = f_col1.slider("Layovers", 0, int(df['Layovers'].max()), int(df['Layovers'].max()))
                selected_airlines = f_col2.multiselect("Airlines", options=sorted(df['Carrier'].unique()), default=df['Carrier'].unique())
                sort_by = f_col2.selectbox("Sort by", ["Price", "Duration"])
                
                df = df[
                    (df['Price'] <= max_p) & 
                    (df['Duration'] <= pd.to_timedelta(max_dur, unit='h')) &
                    (df['Layovers'] <= max_lay) &
                    (df['Carrier'].isin(selected_airlines))
                ].sort_values(sort_by)

            for _, row in df.iterrows():
                offer = st.session_state.flight_results['data'][row['idx']]
                segments = offer['itineraries'][0]['segments']
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"<span class='carrier-text'>{row['Departure'].strftime('%a, %d %b %Y')}</span>", unsafe_allow_html=True)
                        st.markdown(f"<span class='route-text'>{row['Carrier']} | {maps['city'].get(segments[0]['departure']['iataCode'])} ({segments[0]['departure']['iataCode']}) → {maps['city'].get(segments[-1]['arrival']['iataCode'])} ({segments[-1]['arrival']['iataCode']})</span>", unsafe_allow_html=True)
                        st.markdown(f"⏱️ {format_duration(row['Duration'])} | 🔄 {row['Layovers']} Layovers")
                    
                    with c2:
                        # Display raw API price/currency for accuracy
                        curr_map = {"EUR": "€", "USD": "$"}
                        symbol = curr_map.get(row['Currency'], row['Currency'])
                        st.markdown(f"<div class='price-text'>{symbol}{row['Price']:.2f}</div>", unsafe_allow_html=True)
                        if st.button("Book Flight", key=f"bk_{row['idx']}"):
                            token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                            price_res = amadeus.get_flight_price(token, offer)
                            if price_res and 'data' in price_res:
                                st.session_state.priced_offer = price_res['data']['flightOffers'][0]
                                st.session_state.step = 6
                                st.rerun()
                            else:
                                st.error("Could not confirm price. This flight may no longer be available.")

                    with st.expander("View Full Timeline"):
                        for i, seg in enumerate(segments):
                            st.markdown(f"""
                            <div class='timeline-row'>
                                <span class='time-badge'>{seg['departure']['at'][-8:-3]}</span>
                                <span>departing from <span class='city-name'>{maps['city'].get(seg['departure']['iataCode'])}</span> <span class='iata-code'>({seg['departure']['iataCode']})</span></span>
                             </div>
                             <div class='duration-info'>↓ Flight duration: {format_duration(seg['duration'])}</div>
                            <div class='timeline-row'>
                                <span class='time-badge'>{seg['arrival']['at'][-8:-3]}</span>
                                <span>arrival at <span class='city-name'>{maps['city'].get(seg['arrival']['iataCode'])}</span> <span class='iata-code'>({seg['arrival']['iataCode']})</span></span>
                            </div>
                            """, unsafe_allow_html=True)

                            # Calculate Layover if there is a next segment
                            if i < len(segments) - 1:
                                next_seg = segments[i+1]
                                arr_time = datetime.datetime.fromisoformat(seg['arrival']['at'].replace('Z', ''))
                                dep_time = datetime.datetime.fromisoformat(next_seg['departure']['at'].replace('Z', ''))
                                layover_td = dep_time - arr_time
                                
                                # Format layover duration
                                hours, remainder = divmod(int(layover_td.total_seconds()), 3600)
                                minutes, _ = divmod(remainder, 60)
                                layover_str = f"{hours}h {minutes}m"
                                
                                st.markdown(f"<div class='layover-info'>Layover: {layover_str}</div>", unsafe_allow_html=True)

    if st.button("← Back to Results"):
        st.session_state.step = 4
        st.rerun()

def show_booking_step():
    st.header("Confirm Your Booking")
    offer = st.session_state.priced_offer
    counts = st.session_state.get('traveler_counts', {"ADULT": 1, "CHILD": 0, "HELD_INFANT": 0})
    total_passengers = sum(counts.values())
    curr_map = {"EUR": "€", "USD": "$"}
    symbol = curr_map.get(offer['price']['currency'], offer['price']['currency'])
    st.write(f"Total Price: **{symbol}{offer['price']['total']}**")

    with st.form("traveler_form"):
        # Collect contact info once (usually required for the primary traveler)
        email = st.text_input("Contact Email Address")

        travelers = []
        idx = 1
        for p_type, count in counts.items():
            for _ in range(count):
                st.subheader(f"Passenger {idx} ({p_type})")
                fn, ln, dob_col = st.columns([2, 2, 2])
                f_name = fn.text_input(f"First Name", key=f"fn_{idx}")
                l_name = ln.text_input(f"Last Name", key=f"ln_{idx}")
                d_o_b = dob_col.date_input("Date of Birth", value=datetime.date(1990, 1, 1), key=f"dob_{idx}", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
                
                travelers.append({
                    "id": str(idx),
                    "dateOfBirth": d_o_b.strftime("%Y-%m-%d"),
                    "name": {"firstName": f_name.upper(), "lastName": l_name.upper()},
                    "gender": "MALE", # Simplified for this UI
                    "contact": {
                        "emailAddress": email if email else "traveler@example.com",
                        "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": "123456789"}]
                    }
                })
                idx += 1

        if st.form_submit_button("Confirm & Book"):
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not email or not re.match(email_regex, email):
                st.error("🚨 Email Address is invalid")
            else:
                token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                booking_res = amadeus.create_flight_order(token, offer, travelers)
                
                if booking_res and 'data' in booking_res:
                    st.session_state.confirmed_booking = booking_res
                    st.session_state.step = 7
                    st.rerun()
                else:
                    if booking_res and 'errors' in booking_res:
                        for err in booking_res['errors']:
                            detail = err.get('detail', 'Unknown validation error')
                            pointer = err.get('source', {}).get('pointer', '')
                            
                            # Parse the Amadeus pointer (e.g., /data/travelers[0]) to identify the passenger
                            match = re.search(r'travelers\[(\d+)\]|travelerPricings\[(\d+)\]', pointer)
                            if match:
                                # Amadeus uses 0-based indexing; we add 1 for the user-facing Passenger number
                                idx_str = match.group(1) or match.group(2)
                                p_num = int(idx_str) + 1
                                if "lastName format is invalid" in detail:
                                    msg = f"Last Name of Passenger {p_num} is invalid"
                                elif "firstName format is invalid" in detail:
                                    msg = f"First Name of Passenger {p_num} is invalid"
                                elif "TOO_OLD" in detail:
                                    msg = f"Passenger {p_num} is too old"
                                else:
                                    msg = f"Passenger {p_num} Issue: {detail}"
                                st.error(f"🚨 {msg}")
                    else:
                        st.error("Booking failed. The flight may no longer be available or the connection timed out.")

def show_confirmation_step():
    if 'confirmed_booking' in st.session_state:
        st.balloons(); st.success("🎉 Booking Confirmed!")
        pnr = st.session_state.confirmed_booking['data']['associatedRecords'][0]['reference']
        st.subheader(f"Booking Reference (PNR): {pnr}")
    else:
        st.error("No booking record found.")
    if st.session_state.get('google_creds'):
        st.success("✅ Flight added to your Google Calendar!")
    if not st.session_state.get('google_creds') and st.button("Add to Google Calendar 📅"):
        flow = calendar_client.get_google_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
        # Pack both the offer AND the booking into the state so they survive the redirect
        state_payload = {
            "offer": st.session_state.priced_offer,
            "booking": st.session_state.confirmed_booking
        }
        state_data = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
        auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=state_data)
        st.session_state.google_auth_active = True
        auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=state_data)
        st.session_state.google_auth_active = True
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 5. MAIN APP ROUTER
# ==========================================
def run_app():
        # Handle Google OAuth Redirect
    q = st.query_params
    if "code" in q:
        flow = calendar_client.get_google_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
        st.session_state.google_creds = calendar_client.get_credentials_from_code(flow, q.get("state"), q.get("code"))
        
        # Recover offer and create event
        state_decoded = json.loads(base64.urlsafe_b64decode(q["state"]).decode())
        offer = state_decoded.get("offer")
        booking = state_decoded.get("booking")
        
        # Restore these to session state so the UI doesn't crash
        st.session_state.priced_offer = offer
        st.session_state.confirmed_booking = booking
        maps = data_manager.get_iata_mappings()
        service = calendar_client.get_calendar_service(st.session_state.google_creds)
        
        seg = offer['itineraries'][0]['segments']
        calendar_client.create_calendar_event(
            service, f"Flight to {maps['city'].get(seg[-1]['arrival']['iataCode'])}",
            datetime.datetime.fromisoformat(seg[0]['departure']['at'].replace('Z', '')),
            datetime.datetime.fromisoformat(seg[-1]['arrival']['at'].replace('Z', '')),
            maps['city'].get(seg[0]['departure']['iataCode']), maps['city'].get(seg[-1]['arrival']['iataCode']),
            maps['tz'].get(seg[0]['departure']['iataCode'], "UTC"), maps['tz'].get(seg[-1]['arrival']['iataCode'], "UTC")
        )
        st.query_params.clear()
        st.session_state.step = 7
    st.markdown('<div class="main-header">Your Next Adventure Awaits</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">A personalized travel planner for your individual needs.</p>', unsafe_allow_html=True)

    # Initialize session state for multi-step workflow
    if 'step' not in st.session_state:
        st.session_state.step = 1; st.session_state.card_index = 0; st.session_state.conversation = []

    # Step-based router
    if st.session_state.step == 1:
        show_profile_step()
    elif st.session_state.step == 2:
        show_swiping_step()
    elif st.session_state.step == 3:
        show_astro_step()
    elif st.session_state.step == 4:
        show_results_step()
    elif st.session_state.step == 5:
        show_dashboard_step()
    elif st.session_state.step == 6:
        show_booking_step()
    elif st.session_state.step == 7:
        show_confirmation_step()

if __name__ == "__main__":
    run_app()
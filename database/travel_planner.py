import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import random

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
st.set_page_config(
    page_title="Global Travel Planner",
    page_icon="🌏",
    layout="wide",
)

# Custom CSS for styling - Clean & Overlap-free
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        
        /* Global Font */
        html, body, [class*="st-"] { font-family: 'Poppins', sans-serif; }
        
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
        
        /* Cards */
        .card { 
            background-color: white; 
            padding: 1.5rem; 
            border-radius: 12px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
            margin-bottom: 1rem; 
            border: 1px solid #f0f0f0;
        }
        
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

        /* Expander Styling Fix */
        .streamlit-expanderHeader {
            font-weight: 600;
            color: #444;
            background-color: #f8f9fa;
            border-radius: 8px;
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

    def load_base_data(self):
        query = """
        SELECT c.iso2, c.iso3, c.country_name, c.tugo_advisory_state, c.pli_ppp,
               cm.climate_avg_temp_c,
               (SELECT COUNT(*) FROM unesco_heritage_sites u WHERE u.country_iso = c.iso2) as unesco_count
        FROM countries c LEFT JOIN climate_monthly cm ON c.country_name = cm.country_name_climate
        """
        df = pd.read_sql(query, self.get_connection())
        return df

    def get_country_details(self, iso2):
        conn = self.get_connection()
        details = {
            'safety': pd.read_sql("SELECT category, description FROM tugo_safety WHERE iso2 = ?", conn, params=(iso2,)),
            'health': pd.read_sql("SELECT disease_name, description FROM tugo_health WHERE iso2 = ? LIMIT 5", conn, params=(iso2,)),
            'entry': pd.read_sql("SELECT category, description FROM tugo_entry WHERE iso2 = ?", conn, params=(iso2,)),
            'unesco': pd.read_sql("SELECT name, category FROM unesco_heritage_sites WHERE country_iso = ? LIMIT 10", conn, params=(iso2,)),
        }
        conn.close()
        return details

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
    st.markdown("### Step 1: Choose Your Traveller Profile")
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
    
    st.markdown(f"### Step 2: Swipe to Refine Your Choices ({card_index + 1}/{len(SWIPE_CARDS)})")
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
    st.markdown("### Step 3: A Final Touch of Destiny? ✨")
    
    use_astro = st.toggle("Include Horoscope Match")
    if use_astro:
        st.selectbox("Your Zodiac Sign", ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"], key="zodiac_sign")
        st.session_state.weights['astro'] = 0.15 
        st.info("A bit of cosmic dust will be added to your match scores!")
    
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    if st.button("Calculate My Matches! 🚀", use_container_width=True):
        st.session_state.step = 4
        st.rerun()

def show_results_step():
    st.markdown("### Step 4: Your Top Destinations!")
    with st.spinner("Analyzing the globe to find your perfect spot..."):
        df_base = data_manager.load_base_data()
        matcher = TravelMatcher(df_base)
        st.session_state.matched_df = matcher.calculate_match(st.session_state.weights, st.session_state.prefs)

    df = st.session_state.matched_df
    top_5 = df.head(5)
    
    st.balloons()
    st.success(f"**Your #1 Match: {top_5.iloc[0]['country_name']}**")
    
    for i, row in top_5.iterrows():
        with st.container():
            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"#### {i+1}. {row['country_name']}")
                score = row['final_score'] / sum(st.session_state.weights.values()) * 100
                st.markdown(f"**Match Score:** <span style='color:green; font-weight:bold'>{score:.0f}%</span>", unsafe_allow_html=True)
            with c2:
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
    
    details = data_manager.get_country_details(country['iso2'])
    
    tab1, tab2, tab3, tab4 = st.tabs(["🛡️ Safety", "🏥 Health & Visa", "🏛️ Culture", "💰 Budget"])
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

    if st.button("← Back to Results"):
        st.session_state.step = 4
        st.rerun()
    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 5. MAIN APP ROUTER
# ==========================================
def run_app():
    st.markdown('<div class="main-header">Your Next Adventure Awaits</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">A personalized travel planner for your individual needs.</p>', unsafe_allow_html=True)

    # Initialize session state for multi-step workflow
    if 'step' not in st.session_state:
        st.session_state.step = 1
        st.session_state.card_index = 0

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

if __name__ == "__main__":
    run_app()

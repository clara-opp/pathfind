# ============================================================
# Weather Box für Country Overview - FINAL VERSION
# ============================================================

import streamlit as st
from typing import Optional, Dict, Any

def get_first_travel_month(data_manager) -> Optional[int]:
    """Get first travel month from session state"""
    try:
        # Try: start_date (from st.date_input)
        start_date = st.session_state.get('start_date')
        if start_date:
            return start_date.month
        
        # Fallback: travel_dates list
        travel_dates = st.session_state.get('travel_dates')
        if travel_dates and len(travel_dates) > 0:
            first_date = travel_dates[0]
            return first_date.month
        
        return None
    except:
        pass
    return None


def fetch_weather_data(data_manager, country: Dict, month: int) -> Optional[Dict[str, Any]]:
    """
    Fetch weather data from climate_monthly table
    """
    try:
        conn = data_manager.get_connection()
        cursor = conn.cursor()
        
        country_name = country.get('country_name')
        
        if not country_name:
            return None
        
        # Query for exact match
        cursor.execute("""
            SELECT * FROM climate_monthly 
            WHERE country_name_climate = ?
            LIMIT 1
        """, (country_name,))
        
        columns = [description[0] for description in cursor.description]
        result = cursor.fetchone()
        
        if not result:
            # Try fuzzy match
            cursor.execute("""
                SELECT * FROM climate_monthly 
                WHERE country_name_climate LIKE ?
                LIMIT 1
            """, (f"%{country_name}%",))
            result = cursor.fetchone()
        
        conn.close()
        
        if result:
            result_dict = dict(zip(columns, result))
            
            temp_key = f"climate_temp_month_{month}"
            precip_key = f"climate_precip_month_{month}"
            cloud_key = f"climate_cloud_month_{month}"
            
            cloud_pct = result_dict.get(cloud_key, 50)
            if cloud_pct is None:
                cloud_pct = 50
            
            sunshine_hours = (24 - float(cloud_pct) / 100 * 24) if cloud_pct else 12
            
            return {
                "temperature_avg": float(result_dict.get("climate_avg_temp_c") or 0),
                "temperature_daytime": float(result_dict.get(temp_key) or 0),
                "precipitation": float(result_dict.get(precip_key) or 0),
                "sunshine_hours": max(0, sunshine_hours),
                "cloud_pct": float(cloud_pct or 50),
            }
        
        return None
        
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None


def get_month_name(month: int) -> str:
    """Get month name from number"""
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    return months[month - 1] if 1 <= month <= 12 else "Unknown"


def render_weather_box(country: Dict, data_manager) -> None:
    """Render clean weather data box for travel month"""
    
    if not country:
        st.info("🌤️ No country selected")
        return
    
    travel_month = get_first_travel_month(data_manager)
    if not travel_month:
        st.info("🌤️ Select travel dates to see weather information")
        return
    
    weather_data = fetch_weather_data(data_manager, country, travel_month)
    if not weather_data:
        country_name = country.get('country_name', 'Unknown')
        st.warning(f"⚠️ Weather data not available for {country_name}")
        return
    
    month_name = get_month_name(travel_month)
    
    st.markdown("---")
    st.markdown(f"### 🌤️ Weather in {month_name}")
    
    # 4 clean metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🌡️ Daytime", f"{int(weather_data.get('temperature_daytime', 0))}°C")
    
    with col2:
        st.metric("☀️ Sunshine", f"{int(weather_data.get('sunshine_hours', 0))}h")
    
    with col3:
        st.metric("🌧️ Rainfall", f"{int(weather_data.get('precipitation', 0))}mm")
    
    with col4:
        st.metric("☁️ Clouds", f"{int(weather_data.get('cloud_pct', 0))}%")
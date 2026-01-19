# ============================================================
# Weather Box für Country Overview - FINAL VERSION
# ============================================================

import streamlit as st
import sqlite3
import json
from typing import Optional, Dict, Any
import random
import pandas as pd

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


def render_unesco_heritage_box(country, data_manager):
    """UNESCO mit 1 Site oben + Tabelle zum Ausklappen für Auswahl"""
    
    import sqlite3
    import json
    import random
    import pandas as pd
    
    iso3 = country.get('iso3')
    if not iso3:
        return
    
    try:
        conn = sqlite3.connect(data_manager.db_path)
        cursor = conn.cursor()
        
        # ISO3 -> ISO2 Mapping
        cursor.execute("SELECT iso2 FROM countries WHERE iso3 = ?", (iso3,))
        iso2_result = cursor.fetchone()
        if not iso2_result:
            conn.close()
            return
        
        iso2 = iso2_result[0]
        
        # UNESCO Summary laden
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM unesco_by_country
            WHERE iso_code = ?
        """, (iso2,))
        
        result = cursor.fetchone()
        if not result or result[0] == 0:
            conn.close()
            return
        
        count = result[0]
        
        # Detail-Daten
        cursor.execute("""
            SELECT id, name, category, main_image_url, short_description, description
            FROM unesco_heritage_sites
            WHERE country_iso = ?
            ORDER BY name
        """, (iso2,))
        
        all_sites = cursor.fetchall()
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading UNESCO data: {str(e)}")
        return
    
    if not all_sites:
        return
    
    # STATE: Aktuelle ausgewählte Site
    spotlight_key = f"unesco_current_{iso3}"
    
    if spotlight_key not in st.session_state:
        st.session_state[spotlight_key] = random.randint(0, len(all_sites) - 1)
    
    current_site_idx = st.session_state[spotlight_key]
    current_site = all_sites[current_site_idx]
    
    site_id, name, category, main_image_url, short_description, description = current_site
    
    # HEADER
    st.markdown("---")
    st.markdown("### UNESCO World Heritage Site")
    
    # SPOTLIGHT: 1 SITE DISPLAY
    col_img, col_info = st.columns([1.2, 4])
    
    with col_img:
        # Bild oder Travel Emoji
        if main_image_url:
            try:
                st.image(main_image_url, use_container_width=False, width=240)
            except:
                st.markdown(
                    "<div style='background: #e0e0e0; width: 240px; height: 180px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 60px;'>✈️</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div style='background: #e0e0e0; width: 240px; height: 180px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 60px;'>✈️</div>",
                unsafe_allow_html=True
            )
    
    with col_info:
        st.markdown(f"**{name}**")
        
        category_str = str(category) if category else "Mixed"
        is_natural = "natural" in category_str.lower() or "n" in str(category_str).lower()
        badge_icon = "🌿" if is_natural else "🏛️"
        badge_color = "#c8e6c9" if is_natural else "#bbdefb"
        
        st.markdown(
            f"<span style='background: {badge_color}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;'>{badge_icon} {category_str}</span>",
            unsafe_allow_html=True
        )
        
        st.markdown("")
        
        # Short description - first 2 lines
        if short_description:
            lines = short_description.split('\n')[:2]
            desc_preview = '\n'.join(lines)
            st.write(desc_preview)
        
        elif description:
            lines = description.split('\n')[:2]
            desc_preview = '\n'.join(lines)
            st.write(desc_preview)
        
        
        # Navigation - inline buttons
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        with col_btn1:
            if st.button("Prev", key=f"prev_btn_{iso3}", use_container_width=True):
                st.session_state[spotlight_key] = (current_site_idx - 1) % len(all_sites)
                st.rerun()
        
        with col_btn2:
            if st.button("Next", key=f"next_btn_{iso3}", use_container_width=True):
                st.session_state[spotlight_key] = (current_site_idx + 1) % len(all_sites)
                st.rerun()
    
    # EXPANDABLE: ALLE STÄTTEN
    st.markdown("")
    
    with st.expander(f"View all {len(all_sites)} sites", expanded=False):
        
        sites_data = []
        for idx, site in enumerate(all_sites):
            site_id, name, category, main_image_url, short_description, description = site
            category_str = str(category) if category else "Mixed"
            is_natural = "natural" in category_str.lower()
            cat_emoji = "🌿" if is_natural else "🏛️"
            
            sites_data.append({
                "Site": f"{cat_emoji} {name}",
                "Category": category_str,
                "idx": idx
            })
        
        df = pd.DataFrame(sites_data)
        
        # Selectbox
        selected_site = st.selectbox(
            "Select site:",
            options=df["Site"].tolist(),
            key=f"site_select_{iso3}"
        )
        
        selected_idx = df[df["Site"] == selected_site].iloc[0]["idx"]
        
        if st.button("View", key=f"view_site_{iso3}", type="primary", use_container_width=True):
            st.session_state[spotlight_key] = selected_idx
            st.rerun()
        
        # Tabelle
        st.dataframe(
            df[["Site", "Category"]], 
            use_container_width=True,
            hide_index=True,
            height=300
        )

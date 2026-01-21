# ============================================================
# Weather Box für Country Overview - FINAL VERSION
# ============================================================

import streamlit as st
import sqlite3
import json
from typing import Optional, Dict, Any
import random
import pandas as pd
import re
from typing import Optional, Dict, Any
import streamlit as st
import calendar
from datetime import date, datetime

# Known name fixes (extend as needed)
COUNTRY_ALIASES = {
    # examples you mentioned
    "iran": "Islamic Republic of Iran",
    "viet nam": "Vietnam",

    # auto-derived common mismatches between ISO and climate naming (from your files)
    "saint kitts and nevis": "St Kitts and Nevis",
    "vanuatu": "Vanatu",
    "puerto rico": "Puerto Rica",
    "christmas island": "Christmas Isl",
    "sao tome and principe": "Sao Tome + Principe",
    "central african republic": "Central African Rep",
    "norfolk island": "Norfolk Isl",
    "bosnia and herzegovina": "Bosnia-Herzegovinia",
}

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def get_first_travel_month(data_manager=None) -> Optional[int]:
    try:
        start_date = st.session_state.get('start_date')
        if isinstance(start_date, (date, datetime)):
            return start_date.month
        if start_date:  # sometimes date_input returns datetime.date
            return start_date.month

        travel_dates = st.session_state.get('travel_dates')
        if travel_dates and len(travel_dates) > 0 and travel_dates[0]:
            return travel_dates[0].month
    except Exception:
        return None
    return None


def _days_in_selected_month(month: int) -> int:
    # Use selected start_date year if available (leap years)
    start_date = st.session_state.get("start_date")
    year = start_date.year if isinstance(start_date, (date, datetime)) else 2025
    return calendar.monthrange(year, month)[1]


def fetch_weather_data(data_manager, country: Dict, month: int) -> Optional[Dict[str, Any]]:
    """
    Keeps your old 'works most of the time' matching approach,
    but adds a deterministic alias layer and returns precip as month + derived day avg.
    precip in your climate JSON is monthly total (precip_mm). [file:38]
    """
    conn = None
    try:
        conn = data_manager.get_connection()
        cursor = conn.cursor()

        iso3 = country.get('iso3')
        # IMPORTANT: support both keys
        country_name = country.get('country_name') or country.get('countryname')

        if not iso3 and not country_name:
            return None

        matched_climate_country = None

        # Pull all climate country names once (small list)
        cursor.execute("SELECT DISTINCT country_name_climate FROM climate_monthly")
        climate_countries = [row[0] for row in cursor.fetchall() if row and row[0]]

        # normalize once
        climate_norm = {c.lower(): c for c in climate_countries}

        # 0) Alias layer (hard mapping)
        if country_name:
            n = _norm(country_name)
            alias = COUNTRY_ALIASES.get(n)
            if alias and alias.lower() in climate_norm:
                matched_climate_country = climate_norm[alias.lower()]

        # 1) exact match
        if not matched_climate_country and country_name:
            if country_name.lower() in climate_norm:
                matched_climate_country = climate_norm[country_name.lower()]

        # 2) contains match (old behavior)
        if not matched_climate_country and country_name:
            cn = country_name.lower()
            for climate_country in climate_countries:
                cc = climate_country.lower()
                if cn in cc:
                    matched_climate_country = climate_country
                    break

        # 3) reverse contains match (old behavior; but keep it conservative)
        if not matched_climate_country and country_name:
            cn = country_name.lower()
            for climate_country in climate_countries:
                words = [w for w in climate_country.split() if len(w) > 4]
                if any(w.lower() in cn for w in words):
                    matched_climate_country = climate_country
                    break

        # 4) last fallback: LIKE query (old behavior)
        if not matched_climate_country and country_name:
            cursor.execute("""
                SELECT DISTINCT country_name_climate
                FROM climate_monthly
                WHERE country_name_climate LIKE ?
                LIMIT 1
            """, (f"%{country_name}%",))
            match = cursor.fetchone()
            if match:
                matched_climate_country = match[0]

        if not matched_climate_country:
            return None

        cursor.execute("""
            SELECT * FROM climate_monthly
            WHERE country_name_climate = ?
            LIMIT 1
        """, (matched_climate_country,))
        result = cursor.fetchone()
        if not result:
            return None

        columns = [description[0] for description in cursor.description]
        result_dict = dict(zip(columns, result))

        temp_key = f"climate_temp_month_{month}"
        precip_key = f"climate_precip_month_{month}"
        cloud_key = f"climate_cloud_month_{month}"

        cloud_pct = result_dict.get(cloud_key, 50)
        if cloud_pct is None:
            cloud_pct = 50

        sunshine_hours = 24 * (1 - float(cloud_pct) / 100)

        precip_month = float(result_dict.get(precip_key) or 0.0)   # mm/month [file:38]
        days = _days_in_selected_month(month)
        precip_day = precip_month / days if days else 0.0

        return {
            "matched_climate_country": matched_climate_country,
            "temperature_avg": float(result_dict.get("climate_avg_temp_c") or 0),
            "temperature_daytime": float(result_dict.get(temp_key) or 0),
            "precipitation_month_mm": precip_month,  # mm/month
            "precipitation_day_mm": precip_day,      # derived mm/day
            "sunshine_hours": max(0, float(sunshine_hours)),
            "cloud_pct": float(cloud_pct or 50),
        }

    except Exception as e:
        print(f"Weather fetch error for {country.get('country_name') or country.get('countryname')} ({country.get('iso3')}): {e}")
        return None
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_month_name(month: int) -> str:
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    return months[month - 1] if 1 <= month <= 12 else "Unknown"


def render_weather_box(country: Dict, data_manager) -> Optional[Dict[str, Any]]:
    if not country:
        st.info("🌤️ No country selected")
        return None

    travel_month = get_first_travel_month()
    if not travel_month:
        st.info("🌤️ Select travel dates to see weather information")
        return None

    weather_data = fetch_weather_data(data_manager, country, travel_month)
    if not weather_data:
        country_name = country.get('country_name') or country.get('countryname') or 'Unknown'
        st.warning(f"⚠️ Weather data not available for {country_name}")
        return None

    month_name = get_month_name(travel_month)

    st.markdown("---")
    st.markdown(f"### Weather in {month_name}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌡️ Daytime", f"{int(weather_data.get('temperature_daytime', 0))}°C")
    with col2:
        st.metric("☀️ Sunshine", f"{int(weather_data.get('sunshine_hours', 0))}h")
    with col3:
        st.metric("🌧️ Rainfall", f"{int(weather_data.get('precipitation_month_mm', 0))} mm/month")
        st.caption(f"≈ {weather_data.get('precipitation_day_mm', 0):.1f} mm/day")
    with col4:
        st.metric("☁️ Clouds", f"{int(weather_data.get('cloud_pct', 0))}%")

    return weather_data

def render_unesco_heritage_box(country, data_manager):
    
    iso3 = country.get('iso3')
    if not iso3:
        return
    
    try:
        conn = sqlite3.connect(data_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT iso2 FROM countries WHERE iso3 = ?", (iso3,))
        iso2_result = cursor.fetchone()
        if not iso2_result:
            conn.close()
            return
        
        iso2 = iso2_result[0]
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM unesco_by_country
            WHERE iso_code = ?
        """, (iso2,))
        
        result = cursor.fetchone()
        if not result or result[0] == 0:
            conn.close()
            return
        
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
    
    spotlight_key = f"unesco_current_{iso3}"
    
    if spotlight_key not in st.session_state:
        st.session_state[spotlight_key] = random.randint(0, len(all_sites) - 1)
    
    current_site_idx = st.session_state[spotlight_key]
    current_site = all_sites[current_site_idx]
    
    site_id, name, category, main_image_url, short_description, description = current_site
    
    st.markdown("---")
    st.markdown("### UNESCO World Heritage Site")
    
    col_img, col_info = st.columns([1.2, 4])
    
    with col_img:
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
        
        if short_description:
            lines = short_description.split('\n')[:2]
            desc_preview = '\n'.join(lines)
            st.write(desc_preview)
        elif description:
            lines = description.split('\n')[:2]
            desc_preview = '\n'.join(lines)
            st.write(desc_preview)
        
        st.markdown("")
        
        # NAVIGATION - NUR wenn mehr als 1 Site
        if len(all_sites) > 1:
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("◀ Previous", key=f"prev_btn_{iso3}", use_container_width=True):
                    st.session_state[spotlight_key] = (current_site_idx - 1) % len(all_sites)
                    st.rerun()
            
            with col_btn2:
                if st.button("Next ▶", key=f"next_btn_{iso3}", use_container_width=True):
                    st.session_state[spotlight_key] = (current_site_idx + 1) % len(all_sites)
                    st.rerun()
    
    st.markdown("")
    
    # EXPANDABLE - NUR wenn mehr als 1 Site
    if len(all_sites) > 1:
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
            
            selected_site = st.selectbox(
                "Select site:",
                options=df["Site"].tolist(),
                key=f"site_select_{iso3}"
            )
            
            selected_idx = df[df["Site"] == selected_site].iloc[0]["idx"]
            
            if st.button("View", key=f"view_site_{iso3}", type="primary", use_container_width=True):
                st.session_state[spotlight_key] = selected_idx
                st.rerun()
            
            st.dataframe(
                df[["Site", "Category"]], 
                use_container_width=True,
                hide_index=True,
                height=300
            )

def fetch_safety_data(data_manager, country: Dict) -> Optional[Dict[str, Any]]:
    """
    Fetch essential safety and health data from tugo detail tables + equality index
    """
    try:
        conn = data_manager.get_connection()
        cursor = conn.cursor()
        
        iso3 = country.get('iso3')
        iso2 = country.get('iso2')
        
        if not iso2 and not iso3:
            return None
        
        # Fetch critical safety categories (Women's safety FIRST, then others)
        critical_safety = [
            "Women's safety",
            "Terrorism",
            "Crime",
            "Kidnapping",
            "Security situation",
            "2SLGBTQI+ persons",
            "Demonstrations"
        ]
        
        safety_data = []
        for category in critical_safety:
            cursor.execute("""
                SELECT category, description
                FROM tugo_safety
                WHERE iso2 = ? AND category LIKE ?
                LIMIT 1
            """, (iso2, f"%{category}%"))
            result = cursor.fetchone()
            if result:
                safety_data.append(result)
        
        # Fetch key health info (vaccines, diseases)
        cursor.execute("""
            SELECT DISTINCT disease_name
            FROM tugo_health
            WHERE iso2 = ?
            AND disease_name NOT IN ('GENERAL', '')
            ORDER BY disease_name
        """, (iso2,))
        
        diseases = [row[0] for row in cursor.fetchall()]
        
        health_data = []
        for disease in diseases:
            cursor.execute("""
                SELECT disease_name, description
                FROM tugo_health
                WHERE iso2 = ? AND disease_name = ?
                LIMIT 1
            """, (iso2, disease))
            result = cursor.fetchone()
            if result:
                health_data.append(result)
        
        # Fetch equality index data (LGBTQ+ scores)
        equality_data = None
        if iso3:
            cursor.execute("""
                SELECT 
                    equality_index_score,
                    equality_index_legal,
                    equality_index_public_opinion,
                    equality_index_rank
                FROM equality_index
                WHERE iso3 = ?
                LIMIT 1
            """, (iso3,))
            equality_data = cursor.fetchone()
        
        conn.close()
        
        if safety_data or health_data or equality_data:
            return {
                "safety": safety_data,
                "health": health_data,
                "equality": equality_data
            }
        
        return None
        
    except Exception as e:
        print(f"Safety data fetch error for {country.get('country_name')} ({country.get('iso2')}): {e}")
        return None

    

def clean_lgbtq_text(text: str) -> str:
    """
    Standardize LGBTQ+ terminology in text and fix double plusses
    """
    if not text:
        return text
    
    import re
    
    # Replace various LGBTQ+ abbreviations with standard "LGBTQ+"
    text = text.replace("2SLGBTQI+", "LGBTQ+")
    text = text.replace("2SLGBTQI", "LGBTQ+")
    text = text.replace("LGBT+", "LGBTQ+")
    text = text.replace("LGBTQ", "LGBTQ+")
    
    # Fix double plusses (e.g., "LGBTQ+++")
    text = re.sub(r'LGBTQ\+{2,}', 'LGBTQ+', text)
    
    # Fix any word followed by multiple plusses
    text = re.sub(r'(\w)\+{2,}', r'\1+', text)
    
    return text


def format_text(text: str) -> str:
    """
    Format text for better readability: add spaces after periods, fix line breaks
    Remove unnecessary boilerplate text and Canada references
    """
    if not text:
        return text
    
    # Add space after period if missing (but not for abbreviations like "U.S.")
    text = re.sub(r'([a-z])\.([A-Z])', r'\1. \2', text)
    
    # Add newlines before bullet points or numbered lists for better formatting
    text = re.sub(r'(\n| )•', r'\n• ', text)
    text = re.sub(r'(\n| )(?=\d+\.)', r'\n', text)
    
    # Fix multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove boilerplate text
    # Remove "Advice for women travellers" links
    text = re.sub(r'\s*Advice for women travellers\s*', '', text, flags=re.IGNORECASE)
    
    # Remove "Learn more:" sections and links
    text = re.sub(r'\s*Learn more:.*?(?=\n\n|\Z)', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'Learn more.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove "For more information" sentences
    text = re.sub(r'[^.!?]*For more information[^.!?]*[.!?]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^.!?]*See[^.!?]*[.!?]', '', text, flags=re.IGNORECASE)
    
    # Remove sentences containing "Canada" (aber nicht wenn es der einzige Satz ist)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    filtered_sentences = [s for s in sentences if 'Canada' not in s or len(sentences) <= 2]
    text = ' '.join(filtered_sentences)
    
    # Clean up multiple newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Entferne Text nach dem letzten Punkt (unvollständige Sätze am Ende)
    # Finde den letzten Punkt, Fragezeichen oder Ausrufezeichen
    last_punctuation = max(
        text.rfind('.'),
        text.rfind('!'),
        text.rfind('?')
    )
    
    if last_punctuation != -1:
        # Es gibt Punkte im Text
        text = text[:last_punctuation + 1]
        text = text.strip()
    elif text:
        # Kein Punkt gefunden - entferne alles (unvollständiger Text)
        text = ""
    
    return text


def remove_double_star_segments(text: str) -> str:
    if not text:
        return False
    return bool(re.search(r"(^|\n)\s*\*\*", str(text)))



def get_equality_color_and_emoji(score: float) -> tuple[str, str]:
    """Return color and emoji based on equality index score (0-100)"""
    if score is None:
        return "#e0e0e0", "⚪"
    
    score = float(score)
    if score >= 75:
        return "#4caf50", "🟢"  # Green - Very Safe
    elif score >= 50:
        return "#8bc34a", "🟡"  # Light Green - Moderate
    elif score >= 25:
        return "#ff9800", "🟠"  # Orange - Lower
    else:
        return "#f44336", "🔴"  # Red - Very Low



def render_safety_box(country: Dict, data_manager) -> None:
    """
    Render essential safety and health information with LGBTQ+ details in dropdown
    """
    
    if not country:
        st.info("🛡️ No country selected")
        return
    
    safety_data = fetch_safety_data(data_manager, country)
    if not safety_data:
        country_name = country.get('country_name', 'Unknown')
        st.info(f"ℹ️ Safety data not available for {country_name}")
        return
    
    country_name = country.get('country_name', 'Unknown')
    
    st.markdown("---")
    st.markdown("### 🛡️ Safety & Health Essentials")
    
    safety_list = safety_data.get("safety", [])
    health_list = safety_data.get("health", [])
    equality_data = safety_data.get("equality")
    
    # TABS: Safety / Health
    tab1, tab2 = st.tabs(["⚠️ Safety Alerts", "💊 Health Risks"])
    
    with tab1:
        # Women's safety - expandable
        for category, description in safety_list:
            if "Women" in category:
                with st.expander(f"👩 {category}", expanded=True):
                    st.write(format_text(description))
                st.markdown("")
                break
        
        # Other safety alerts (not women, not lgbtq, not driving)
        for category, description in safety_list:
            if ("Women" not in category and 
                "2SLGBTQI+" not in category and 
                "Driving" not in category):
                with st.expander(f"⚠️ {category}"):
                    st.write(format_text(description))
        
        # LGBTQ+ safety - as regular expander like others
        lgbtq_alert = None
        for category, description in safety_list:
            if "2SLGBTQI+" in category:
                lgbtq_alert = (category, description)
                break
        
        if equality_data or lgbtq_alert:
            with st.expander(f"🏳️‍🌈 LGBTQ+ Safety & Index"):
                col1, col2 = st.columns([1, 2])
                
                # Left: Score boxes
                with col1:
                    if equality_data:
                        overall_score, legal_score, social_score, rank = equality_data
                        
                        if overall_score is not None:
                            color, emoji = get_equality_color_and_emoji(overall_score)
                            
                            # Overall score
                            st.markdown(
                                f"<div style='background: {color}; padding: 12px; border-radius: 6px; margin-bottom: 8px;'>"
                                f"<div style='font-size: 12px; color: #666;'>Overall</div>"
                                f"<div style='font-size: 24px; font-weight: bold;'>{overall_score:.0f}/100</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            
                            # Legal Rights
                            if legal_score:
                                legal_color, _ = get_equality_color_and_emoji(legal_score)
                                st.markdown(
                                    f"<div style='background: {legal_color}; padding: 8px; border-radius: 6px; margin-bottom: 6px;'>"
                                    f"<div style='font-size: 10px; color: #666;'>Legal</div>"
                                    f"<div style='font-size: 16px; font-weight: bold;'>{legal_score:.0f}</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            
                            # Social Acceptance
                            if social_score:
                                social_color, _ = get_equality_color_and_emoji(social_score)
                                st.markdown(
                                    f"<div style='background: {social_color}; padding: 8px; border-radius: 6px;'>"
                                    f"<div style='font-size: 10px; color: #666;'>Social</div>"
                                    f"<div style='font-size: 16px; font-weight: bold;'>{social_score:.0f}</div>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                            
                            if rank:
                                st.caption(f"🌍 Rank: #{rank}")
                
                # Right: Text content
                with col2:
                    if lgbtq_alert:
                        category, description = lgbtq_alert
                        # Clean up description: replace LGBTQ variations
                        cleaned_desc = clean_lgbtq_text(description)
                        st.write(format_text(cleaned_desc))
                    else:
                        st.info("No specific LGBTQ+ information available")
        
        # Driving information
        driving_info = None
        for category, description in safety_list:
            if "Driving" in category:
                driving_info = (category, description)
                break
        
        if driving_info:
            category, description = driving_info
            with st.expander(f"🚗 {category}"):
                st.write(format_text(description))
    
    with tab2:
        # Important travel diseases to filter for (COVID-19 removed)
        important_diseases = [
            "Malaria",
            "Dengue",
            "Zika",
            "Typhoid",
            "Hepatitis",
            "Rabies",
            "Tuberculosis",
            "Measles",
            "Polio",
            "Cholera"
        ]
        
        if health_list:
            # Filter and show only important diseases
            important_found = []
            other_found = []
            
            for disease_name, description in health_list:
                # Skip COVID-19
                if "COVID" in disease_name or "covid" in disease_name.lower():
                    continue
                 # Skip Yellow Fever komplett
                if "yellow fever" in disease_name.lower():
                    continue

                # Skip alle verbuggten Einträge (enthält ** irgendwo)
                if remove_double_star_segments(description):
                    continue

                is_important = any(
                    disease.lower() in disease_name.lower() 
                    for disease in important_diseases
                )
                
                if is_important:
                    important_found.append((disease_name, description))
                else:
                    other_found.append((disease_name, description))
            
            # Show important diseases first
            if important_found:
                for disease_name, description in important_found:
                    with st.expander(f"🦟 {disease_name}"):
                        st.write(format_text(description))
            
            # Show other diseases collapsed
            if other_found:
                with st.expander("ℹ️ Other Health Information"):
                    for disease_name, description in other_found:
                        st.markdown(f"**{disease_name}**")
                        st.write(format_text(description))
                        st.markdown("")
        else:
            st.info("No specific disease risks identified")

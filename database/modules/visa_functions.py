# ============================================================
# FÜR country_overview.py - PRODUCTION VERSION
# ============================================================

import requests
import os
from typing import Optional, Dict, Any
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

TRAVEL_BUDDY_API_KEY = os.getenv("TRAVEL_BUDDY_API_KEY")
TRAVEL_BUDDY_API_HOST = "visa-requirement.p.rapidapi.com"


@st.cache_data(ttl=86400)
def fetch_visa_requirements(passport_iso2: str, destination_iso2: str) -> Optional[Dict[str, Any]]:
    """Fetch visa requirements from Travel Buddy API"""
    
    api_key = TRAVEL_BUDDY_API_KEY
    
    if not api_key:
        return None
    
    url = "https://visa-requirement.p.rapidapi.com/v2/visa/check"
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "visa-requirement.p.rapidapi.com",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    payload = {
        "passport": passport_iso2.upper(),
        "destination": destination_iso2.upper()
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=10,
            allow_redirects=True
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success" or data.get("data"):
            return data.get("data", {})
        else:
            return None
            
    except Exception as e:
        return None


def format_visa_info(visa_data: Dict[str, Any]) -> Dict[str, str]:
    """Format visa API response into readable information"""
    
    result = {}
    
    destination = visa_data.get("destination", {})
    result["destination_name"] = destination.get("name", "Unknown")
    result["capital"] = destination.get("capital", "N/A")
    result["currency"] = destination.get("currency", "N/A")
    result["passport_validity"] = destination.get("passport_validity", "N/A")
    
    mandatory_reg = visa_data.get("mandatory_registration", {})
    if mandatory_reg:
        result["mandatory_registration"] = mandatory_reg.get("name", "N/A")
        result["mandatory_reg_link"] = mandatory_reg.get("link", "")
    else:
        result["mandatory_registration"] = None
    
    visa_rules = visa_data.get("visa_rules", {})
    
    primary_rule = visa_rules.get("primary_rule", {})
    result["primary_visa_name"] = primary_rule.get("name", "Not specified")
    result["primary_duration"] = primary_rule.get("duration", "")
    result["primary_color"] = primary_rule.get("color", "blue")
    result["primary_link"] = primary_rule.get("link", "")
    
    secondary_rule = visa_rules.get("secondary_rule", {})
    if secondary_rule:
        result["secondary_visa_name"] = secondary_rule.get("name", "")
        result["secondary_duration"] = secondary_rule.get("duration", "")
        result["secondary_link"] = secondary_rule.get("link", "")
    
    return result


def color_to_emoji(color: str, visa_name: str = "") -> str:
    """Convert color code to emoji - handle E-visa special case"""
    
    # E-visa sollte grün sein, nicht blau (API gibt manchmal blue zurück)
    if "evisa" in visa_name.lower() or "e-visa" in visa_name.lower():
        return "🟢"
    
    color_map = {
        "green": "🟢",
        "blue": "🔵",
        "yellow": "🟡",
        "red": "🔴",
    }
    return color_map.get(color, "⚪")



def render_visa_requirements(country: Dict, passport_iso2: Optional[str] = None):
    """Render visa requirements box with Travel Buddy API data"""
    
    if passport_iso2 is None:
        passport_iso2 = st.session_state.get('passport_iso2')
    
    if not passport_iso2:
        st.info("💡 **Visa Requirements**: Select your nationality in the first step to see visa info")
        return
    
    # Get destination iso2 from country dict
    destination_iso2 = country.get('iso2')
    if not destination_iso2:
        return
    
    st.markdown("---")
    
    # Show nationality info
    nationality_name = st.session_state.get('nationality_name', 'Unknown')
    
    st.markdown(f"### 🛂 Your Personal Visa Requirements")
    st.caption(f"**Your nationality:** {nationality_name}")
    
    with st.spinner("Loading visa information..."):
        visa_data = fetch_visa_requirements(passport_iso2, destination_iso2)
    
    if not visa_data:
        st.info("💡 Could not load visa information. Please check your nationality selection.")
        return
    
    try:
        visa_info = format_visa_info(visa_data)
    except Exception as e:
        st.error(f"Error formatting visa info: {e}")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        with st.container(border=True):
            st.markdown("#### Visa Status")
            
            primary_emoji = color_to_emoji(visa_info.get("primary_color", "blue"), visa_info.get("primary_visa_name", ""))
            primary_name = visa_info.get("primary_visa_name", "Not specified")
            primary_duration = visa_info.get("primary_duration", "")
            
            if primary_duration:
                visa_text = f"**{primary_name}** – {primary_duration}"
            else:
                visa_text = f"**{primary_name}**"
            
            st.markdown(f"{primary_emoji} {visa_text}")
            
            secondary_name = visa_info.get("secondary_visa_name")
            if secondary_name:
                secondary_duration = visa_info.get("secondary_duration", "")
                if secondary_duration:
                    sec_text = f"**{secondary_name}** – {secondary_duration}"
                else:
                    sec_text = f"**{secondary_name}**"
                st.markdown(f"*or* {sec_text}")
    
    with col2:
        with st.container(border=True):
            st.markdown("#### Entry Requirements")
            
            passport_validity = visa_info.get("passport_validity", "N/A")
            st.markdown(f"**Passport valid for:** {passport_validity}")
    
    # All important links in one box
    primary_link = visa_info.get("primary_link")
    mandatory_reg_link = visa_info.get("mandatory_reg_link")
    mandatory_reg_name = visa_info.get("mandatory_registration")
    
    if primary_link or mandatory_reg_link:
        with st.expander("🔗 Important Links"): 
            
            if primary_link:
                st.markdown(f"**📧 Apply for Visa**")
                st.markdown(f"[→ {primary_name} Application Portal]({primary_link})")
                st.caption("Official visa application portal")
                st.markdown("")
            
            if mandatory_reg_link and mandatory_reg_name:
                st.markdown(f"**📋 Mandatory Registration**")
                st.markdown(f"[→ {mandatory_reg_name} Registration]({mandatory_reg_link})")
                st.caption("Required before or upon arrival")
    
    # Visa Status Legend
    with st.expander("ℹ️ Visa Status Legend"):
        st.markdown("""
        **Visa Type Indicators:**
        - 🟢 **Green** - Visa-free, E-visa, or e-Residence (easiest entry, online)
        - 🔵 **Blue** - Standard visa required (apply in advance, longer process)
        - 🟡 **Yellow** - Visa on arrival available (instant, at border)
        - 🔴 **Red** - Complicated, restricted, or difficult visa process
        - ⚪ **Grey** - Status unclear or not available
        
        **Duration**: Shows how long you can stay visa-free or with the visa.
        """)
    
    st.caption(
        "💡 *Information provided by Travel Buddy API. Always verify current requirements "
        "with your embassy before traveling.*"
    )
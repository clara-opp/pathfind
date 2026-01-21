"""
Country Overview Module - Visual dashboard, chatbot, and PDF export
"""
import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
from openai import OpenAI  
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from modules.visa_functions import render_visa_requirements
from modules.info_boxes import render_weather_box, render_unesco_heritage_box, render_safety_box


def render_country_overview(country, data_manager, openai_client, amadeus, amadeus_api_key, amadeus_api_secret, trip_planner_render=None):
    """
    Main entry point - Hero Section ZWISCHEN Back + Start Over buttons
    """
    nav_col1, hero_col, nav_col2 = st.columns([0.15, 0.70, 0.15])
    
    with nav_col1:
        if st.button("Back to Results", key="dashboard_back", use_container_width=True, help="Return to results"):
            st.session_state["is_direct_selection"] = False  # ← RESET FLAG
            st.session_state.step = 6
            st.rerun()
    
    with hero_col:
        render_hero_section(country)
    
    with nav_col2:
        if st.button("Start Over", key="dashboard_start_over", use_container_width=True, help="Reset and begin again"):
            st.session_state.step=1
            st.rerun()
    
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Country Overview", 
        "🌐 AI Assistant", 
        "💰 Budget Planner",
        "🗺️ Plan Trips",
        "✈️ Book Flights",
        "Download PDF"
    ])

    tab_css = """
    <style>
        /* Make tab container full width */
        .stTabs {
            width: 100% !important;
        }
        
        /* Tab list - full width, no gaps */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0 !important;
            width: 100% !important;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Individual tabs - stretched, transparent */
        .stTabs [data-baseweb="tab"] {
            height: auto !important;
            flex-grow: 1 !important;
            background-color: transparent !important;
            border: none !important;
            border-bottom: 3px solid transparent !important;
            color: var(--text-color, #31333F) !important;
            font-weight: 500 !important;
            padding: 14px 20px !important;
            margin: 0 !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
        }
        
        /* Tab hover state */
        .stTabs [data-baseweb="tab"]:hover {
            border-bottom-color: var(--primary-color, #1f6e8a) !important;
            background-color: rgba(31, 110, 138, 0.08) !important;
        }
        
        /* Active tab - colored bottom border */
        .stTabs [aria-selected="true"] [data-baseweb="tab"] {
            border-bottom-color: var(--primary-color, #1f6e8a) !important;
            color: var(--primary-color, #1f6e8a) !important;
            background-color: rgba(31, 110, 138, 0.05) !important;
        }
        
        /* Tab content - semi-transparent background + border */
        .stTabs [data-baseweb="tab-panel"] {
            padding: 24px !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            border-top: 3px solid var(--primary-color, #1f6e8a) !important;
            border-radius: 0 0 8px 8px !important;
            background-color: rgba(255, 255, 255, 0.4) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
        }
        
        /* Remove extra padding/margin */
        .stTabs [data-baseweb="tabs"] {
            margin-bottom: 0 !important;
            width: 100% !important;
        }
    </style>
    """
    st.markdown(tab_css, unsafe_allow_html=True)
    
    
    with tab1:
        render_overview_tab(country, data_manager)
    
    with tab2:
        render_chatbot_tab(country, openai_client, data_manager)
    
    with tab3:
        render_budget_tab(country, data_manager)

    with tab4:
        if trip_planner_render:
            trip_planner_render()
    
    with tab5:
        # Import existing flight search - KEEP INLINE
        from modules.flight_search import render_flight_search
        iso3 = country.get('iso3') or "NA"
        render_flight_search(
            country=country,
            data_manager=data_manager,
            amadeus=amadeus,
            amadeus_api_key=amadeus_api_key,
            amadeus_api_secret=amadeus_api_secret,
            currency_code="USD" if st.session_state.get('origin_iata') == "ATL" else "EUR",
            origin_iata_default=st.session_state.get('origin_iata', 'FRA'),
            start_date_default=st.session_state.get('start_date'),
            end_date_default=st.session_state.get('end_date'),
            image_urls=(country.get('img_1'), country.get('img_2'), country.get('img_3')),
            key_prefix=f"fs_{iso3}"
        )
    
    with tab6:
        render_pdf_tab(country, data_manager)


def render_hero_section(country):
    """
    Hero section:
    LEFT: Flag (flagsapi.com) + Country Name + Match Score
    RIGHT: Travel Safety
    """
    
    # Get ISO2 from country data
    iso2 = country.get('iso2')
    
    col_left, col_right = st.columns([3, 1])
    
    with col_left:
        country_name = country.get('country_name', 'Unknown')
        
        # Build markdown with flag image from flagsapi.com (flat style, 64px)
        if iso2:
            flag_url = f"https://flagsapi.com/{iso2}/flat/64.png"
            st.markdown(
                f'<img src="{flag_url}" width="50" style="margin-right: 10px; vertical-align: middle;"> **{country_name}**', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"# 🌍 {country_name}")
        
        # Only show match score if NOT directly selected
        is_direct = st.session_state.get("is_direct_selection", False)
        if not is_direct:
            score = country.get("final_score", 0) * 100
            st.caption(f"Match Score: {score:.0f}%")

    
    with col_right:
        # Get safety score
        safety_score = country.get('tugo_score')
        advisory = country.get('tugo_advisory_state', 'Unknown')
        advisory = str(advisory) if pd.notna(advisory) else 'Unknown'
        
        # ✅ FIX: If tugo_score is empty but advisory contains a number, use it
        if (safety_score is None or pd.isna(safety_score)) and advisory.replace('.', '', 1).replace('-', '', 1).isdigit():
            try:
                safety_score = float(advisory)
            except:
                pass
        
        # Determine emoji and description based on score
        if safety_score is not None and pd.notna(safety_score):
            try:
                safety_score = float(safety_score)
                
                if safety_score == 0.0:
                    emoji = "🟢"
                    safety_desc = "Very Safe - No significant travel warnings."
                elif safety_score <= 1.0:
                    emoji = "✅"
                    safety_desc = "Safe - Exercise normal precautions."
                elif safety_score <= 2.0:
                    emoji = "⚠️"
                    safety_desc = "Caution - Exercise increased caution due to risks."
                else:  # safety_score >= 3.0
                    emoji = "🚨"
                    safety_desc = "High Risk - Reconsider travel due to serious safety concerns."
            except (ValueError, TypeError):
                # Fallback to text-based logic
                if "exercise normal" in advisory.lower():
                    emoji = "✅"
                    safety_desc = "Safe - Exercise normal precautions."
                elif "high degree" in advisory.lower() or "increased" in advisory.lower():
                    emoji = "⚠️"
                    safety_desc = "Caution - Exercise increased caution due to risks."
                else:
                    emoji = "⚠️"
                    safety_desc = f"{advisory}"
        else:
            # No score available - use text-based logic
            if "exercise normal" in advisory.lower():
                emoji = "✅"
                safety_desc = "Safe - Exercise normal precautions."
            elif "high degree" in advisory.lower() or "increased" in advisory.lower():
                emoji = "⚠️"
                safety_desc = "Caution - Exercise increased caution due to risks."
            else:
                emoji = "⚠️"
                safety_desc = f"{advisory}"
        
        st.metric("🛡️ Travel Safety", emoji, help=f"{safety_desc}\n\nFull Advisory: {advisory}")



def render_overview_tab(country, data_manager):
    """Main overview with visual cards and personalized info"""
    
    # Why This Match?
    st.markdown("### 🎯 Why This Match?")
    render_match_reasons(country)
    
    st.markdown("---")
    
    # Two tabs: Country Information & Requirements and Precautions
    tab_info, tab_requirements = st.tabs(["📍 Country Information", "⚠️ Requirements and Precautions"])
    
    with tab_info:
        # Visual Highlight Cards
        st.markdown("### ✨ Key Highlights")
        render_highlight_cards(country)
        
        #Load data for match reasons
        weather_data = render_weather_box(country, data_manager)
        st.session_state["weather_data"] = weather_data

        render_unesco_heritage_box(country, data_manager)
    
    with tab_requirements:
        # Visa requirements first
        render_visa_requirements(country)
        
        st.markdown("")
        
        # Safety information below
        render_safety_box(country, data_manager)
    
    st.markdown("---")
    
    # Just show the tip without the full Quick Reference section
    st.markdown("### 💡 Tip")
    st.success("Use our Budget Planner, Flight Planner and AI Assistant to plan your trip!")


def render_match_reasons(country):
    """Show personalized reasons why this country matched"""
    persona = st.session_state.get('selected_persona', 'Traveler')
    tarot = st.session_state.get('tarot_card', {}).get('name', None)
    
    reasons = []
    
    # Based on persona
    if 'Budget' in persona:
        col_idx = country.get('numbeo_cost_of_living_index')
        if col_idx and col_idx < 70:
            reasons.append("💰 **Low cost of living** - Perfect for budget travelers")
    
    if 'Culture' in persona or 'Story' in persona:
        unesco = country.get('unesco_count', 0)
        if unesco > 5:
            reasons.append(f"🏛️ **{unesco} UNESCO sites** - Rich cultural heritage")
    
    if 'Clean Air' in persona or 'Calm' in persona:
        pol = country.get('numbeo_pollution_index', 50)
        if pol < 40:
            reasons.append("🌬️ **Clean air quality** - Low pollution levels")
    
    # Based on swipe preferences
    prefs = st.session_state.get("prefs", {})
    targettemp = float(prefs.get("targettemp", 25) or 25)

    weather = st.session_state.get("weather_data") or {}
    actualtemp = weather.get("temperature_daytime")

    if actualtemp is not None and abs(targettemp - float(actualtemp)) < 5:
        reasons.append(f"🌡️ **Perfect weather** - {float(actualtemp):.0f}°C matches your preference")
    
    # Based on tarot
    if tarot and country.get('iso3') in st.session_state.get('tarot_boosted_countries', []):
        reasons.append(f"✨ **Cosmic alignment** - Blessed by *{tarot}*")
    
    if reasons:
        for r in reasons:
            st.markdown(f"- {r}")
    else:
        st.info("✅ This destination scored highly across your preferences!")


def render_highlight_cards(country):
    """Visual cards for key statistics"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("#### Budget")
            col_idx = country.get('numbeo_cost_of_living_index', 50)
            # Invert for display: lower cost = higher bar
            budget_score = max(0, 150 - col_idx) / 150
            st.progress(min(budget_score, 1.0))
            st.caption(f"Cost of living: {col_idx:.0f} (100 = NYC)")
            if col_idx < 50:
                st.success("💰 Very affordable!")
            elif col_idx < 80:
                st.info("💵 Moderate pricing")
            else:
                st.warning("💸 Premium destination")
    
    
    with col2:
        with st.container(border=True):
            st.markdown("#### Healthcare")
            
            # ✅ Use same logic as PDF - try multiple field names
            hc_raw = country.get('numbeo_healthcare_index')
            
            # If not found, search for any field containing 'health'
            if hc_raw is None or pd.isna(hc_raw):
                for key in country.keys():
                    if 'health' in key.lower():
                        val = country.get(key)
                        if val is not None and not pd.isna(val):
                            hc_raw = val
                            break
            
            # Try to get numeric value, fallback to 50
            if hc_raw is not None and pd.notna(hc_raw):
                try:
                    hc = float(hc_raw)
                except (ValueError, TypeError):
                    hc = 50
            else:
                hc = 50
            
            st.progress(min(hc/100, 1.0))
            st.caption(f"Healthcare quality: {hc:.0f}/100")
            
            if hc > 70:
                st.success("🏥 Excellent healthcare")
            elif hc > 50:
                st.info("⚕️ Good healthcare")
            else:
                st.warning("📋 Basic healthcare")


    
    with col3:
        with st.container(border=True):
            st.markdown("#### Air Quality")
            pol = country.get('numbeo_pollution_index', 50)
            air_score = max(0, 100 - pol)
            st.progress(air_score/100)
            st.caption(f"Air quality: {air_score:.0f}/100")
            if air_score > 60:
                st.success("🌿 Fresh air!")
            elif air_score > 40:
                st.info("🌤️ Moderate")
            else:
                st.warning("😷 Consider air quality")


def render_quick_reference(country, data_manager):
    """Quick reference info - NO TABLES, just clean text"""
    
    # ✅ GET ADVISORY AND SCORE FIRST
    safety_score = country.get('tugo_score')
    advisory = country.get('tugo_advisory_state', 'Unknown')
    advisory = str(advisory) if pd.notna(advisory) else 'Unknown'
    
    # Convert to int for comparison
    if safety_score is not None and pd.notna(safety_score):
        safety_score = int(safety_score)
    
    if safety_score == 1:
        safety_desc = "✅ **Safe to Travel** - Exercise normal precautions like you would at home."
    elif safety_score == 2:
        safety_desc = "⚠️ **Exercise Caution** - Increased risks present; stay informed and alert."
    elif safety_score == 3:
        safety_desc = "🚨 **High Risk** - Serious safety concerns; reconsider non-essential travel."
    else:
        safety_desc = f"**{advisory}**"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🛡️ Safety Advisory**")
        st.info(safety_desc)
        
        st.markdown("**🏛️ Culture**")
        unesco_count = int(country.get('unesco_count', 0))
        if unesco_count > 0:
            st.success(f"{unesco_count} UNESCO World Heritage Sites")
        else:
            st.info("Explore local culture and attractions")
    
    with col2:
        st.markdown("**💉 Health**")
        st.info("Consult your doctor for recommended vaccinations before travel.")
        
        st.markdown("**💡 Tip**")
        st.success("Use our Budget Planner, Flight Pleanner and AI Assistant to plan your trip!")




def render_budget_tab(country, data_manager):
    """Cost estimator - keeps existing functionality"""
    from modules.cost_estimator import render_cost_estimator
    
    start_date = st.session_state.get('start_date')
    end_date = st.session_state.get('end_date')
    days_default = 7
    
    if start_date and end_date:
        try:
            days_default = max(1, int((end_date - start_date).days))
        except Exception:
            days_default = 7
    
    iso3 = country.get('iso3')
    if not iso3:
        st.warning("No ISO3 found for this country - cannot run the cost estimator.")
        return
    
    # Reset cost estimator state if country changed
    prev_iso3 = st.session_state.get('ce_active_iso3')
    if prev_iso3 != iso3:
        # Clear previous cost estimator state
        for k in list(st.session_state.keys()):
            if k.startswith('ce_'):
                del st.session_state[k]
        st.session_state['ce_active_iso3'] = iso3
        st.rerun()
    
    # Render the cost estimator - FIX: use db_path with underscore
    render_cost_estimator(
        iso3=iso3,
        days_default=days_default,
        adults_default=2,
        kids_default=0,
        db_path=data_manager.db_path,  # ✅ FIXED: was dbpath
        key_prefix=f"ce_{iso3}"
    )


def render_chatbot_tab(country, openai_client, data_manager):
    """AI-powered trip planning chatbot"""
    st.markdown("### 🌐 Your AI Travel Assistant")
    
    # ✅ Get all data FIRST before using it
    persona = st.session_state.get('selected_persona', 'Traveler')
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))
    duration = (end_date - start_date).days
    
    # Get tarot info if exists
    tarot_card = st.session_state.get('tarot_card', {})
    tarot_hint = ""
    if tarot_card.get('name'):
        orientation = "reversed" if tarot_card.get('is_reversed') else "upright"
        tarot_hint = f",  cosmic guidance **{tarot_card['name']}** ({orientation})"
    
    # NOW you can use tarot_hint
    st.info(f"✨ **Personalized for you!** This assistant knows your travel style (*{persona}*), dates ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}){tarot_hint}, and all of your other stated preferences to give you tailored recommendations.")
        
    # Initialize chat history per country
    chat_key = f"chat_{country['iso3']}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
        
        # Welcome message with all context
        # Get top priorities
        weights = st.session_state.get('weights', {})
        top_priorities = sorted(
            [(k.replace('_', ' ').title(), v) for k, v in weights.items() if v > 0.10],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        priorities_text = ", ".join([p[0] for p in top_priorities])

        st.session_state[chat_key].append({
            "role": "assistant",
            "content": f"Hi! I'm your AI assistant for **{country['country_name']}**! I can help you with:\n\n"
                    "- 🌡️ Climate patterns and best times to visit\n"
                    "- 🍽️ Food culture and regional specialties\n"
                    "- 🚇 Transportation tips for your pace\n"
                    "- 💡 Safety advice & cultural tips\n\n"
                    "What would you like to explore first?"
        })

    
    # Display chat history
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about itinerary, transportation, food, etc."):
        # Add user message
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_ai_travel_response(prompt, country, openai_client, chat_key, data_manager)
                st.markdown(response)
        
        st.session_state[chat_key].append({"role": "assistant", "content": response})
        st.rerun()


def get_tugo_context_for_ai(country, data_manager):
    """
    Query TuGo detail tables and return formatted context for AI.
    Returns a string with relevant health, safety, and law information.
    """
    iso2 = country.get("iso2")
    if not iso2:
        return ""
    
    try:
        details = data_manager.get_country_details(iso2)
    except Exception as e:
        print(f"Error fetching TuGo details: {e}")
        return ""
    
    context_parts = []
    
    # Health warnings (top 5 most critical)
    # FIX: Use "tugo_health" instead of "health"
    if "tugo_health" in details and not details["tugo_health"].empty:
        health_items = details["tugo_health"].head(5)
        if len(health_items) > 0:
            context_parts.append("\n**Health & Vaccination Information:**")
            for idx, row in health_items.iterrows():
                disease = row.get("disease_name", "").strip()
                desc = row.get("description", "").strip()
                if disease and disease != "GENERAL":
                    context_parts.append(f"- {disease}: {desc[:150]}")
                elif desc:
                    context_parts.append(f"- {desc[:150]}")
    
    # Safety concerns (top 5)
    # FIX: Use "tugo_safety" instead of "safety"
    if "tugo_safety" in details and not details["tugo_safety"].empty:
        safety_items = details["tugo_safety"].head(5)
        if len(safety_items) > 0:
            context_parts.append("\n**Safety Concerns:**")
            for idx, row in safety_items.iterrows():
                category = row.get("category", "").strip()
                desc = row.get("description", "").strip()
                if desc:
                    context_parts.append(f"- {category}: {desc[:150]}")
    
    # Laws and cultural norms (top 5)
    # FIX: Use "tugo_laws" instead of "laws"
    if "tugo_laws" in details and not details["tugo_laws"].empty:
        law_items = details["tugo_laws"].head(5)
        if len(law_items) > 0:
            context_parts.append("\n**Important Local Laws & Cultural Norms:**")
            for idx, row in law_items.iterrows():
                category = row.get("category", "").strip()
                desc = row.get("description", "").strip()
                if desc:
                    context_parts.append(f"- {category}: {desc[:150]}")
    
    # Entry requirements
    # FIX: Use "tugo_entry" instead of "entry"
    if "tugo_entry" in details and not details["tugo_entry"].empty:
        entry_items = details["tugo_entry"].head(3)
        if len(entry_items) > 0:
            context_parts.append("\n**Entry/Exit Requirements:**")
            for idx, row in entry_items.iterrows():
                category = row.get("category", "").strip()
                desc = row.get("description", "").strip()
                if desc:
                    context_parts.append(f"- {category}: {desc[:150]}")
    
    return "\n".join(context_parts) if context_parts else ""



def get_ai_travel_response(user_query, country, openai_client, chat_key, data_manager):
    """Generate AI response with comprehensive user context"""
    
    # Core user profile
    persona = st.session_state.get('selected_persona', 'Traveler')
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))
    duration = (end_date - start_date).days
    
    # Get user preferences from swipes
    prefs = st.session_state.get('prefs', {})
    target_temp = prefs.get('target_temp', 25)
    food_style = prefs.get('foodstyle')
    night_style = prefs.get('nightstyle')
    move_style = prefs.get('movestyle')
    
    # Get weights to understand priorities
    weights = st.session_state.get('weights', {})
    top_priorities = sorted(
        [(k, v) for k, v in weights.items() if v > 0.10],
        key=lambda x: x[1],
        reverse=True
    )[:3]
    priority_text = ", ".join([k.replace('_', ' ').title() for k, v in top_priorities])
    
    # Tarot/Astro context
    tarot_card = st.session_state.get('tarot_card', {})
    tarot_name = tarot_card.get('name')
    tarot_travel_meaning = tarot_card.get('travel_meaning', '').strip()
    is_reversed = tarot_card.get('is_reversed', False)
    
    # Build astro sentence if tarot was drawn
    astro_sentence = ""
    if tarot_name:
        orientation = "reversed" if is_reversed else "upright"
        astro_sentence = f"The cosmos blessed this journey with the {tarot_name} ({orientation}): \"{tarot_travel_meaning[:200]}...\""
    
    # Build preference summary
    pref_summary = []
    if food_style == 'eatout':
        pref_summary.append("loves dining out at restaurants")
    elif food_style == 'cook':
        pref_summary.append("prefers cooking/groceries over restaurants")
    
    if night_style == 'party':
        pref_summary.append("enjoys nightlife and party scenes")
    elif night_style == 'chill':
        pref_summary.append("prefers quiet evenings over nightlife")
    
    if move_style == 'walk':
        pref_summary.append("likes walking and exploring on foot")
    
    if target_temp < 20:
        pref_summary.append(f"enjoys cooler weather (~{target_temp}°C)")
    elif target_temp > 26:
        pref_summary.append(f"loves warm weather (~{target_temp}°C)")
    
    pref_text = "; ".join(pref_summary) if pref_summary else "balanced preferences"
    
    # Get detailed TuGo context
    tugo_details = get_tugo_context_for_ai(country, data_manager)

    # Build comprehensive system prompt
    system_prompt = f"""You are an expert travel assistant helping plan a trip to {country['country_name']}.

TRAVELER PROFILE:
- Type: {persona}
- Trip Duration: {duration} days ({start_date.strftime("%B %d")} to {end_date.strftime("%B %d, %Y")})
- Top Priorities: {priority_text}
- Specific Preferences: {pref_text}
{f"- Cosmic Guidance: {astro_sentence}" if astro_sentence else ""}

DESTINATION CONTEXT:
- Safety Advisory: {country.get("tugo_advisory_state", "Unknown")}
- Climate: {country.get("climate_avg_temp_c", "N/A")}°C average
- UNESCO Sites: {country.get("unesco_count", 0)}
- Cost of Living Index: {country.get("numbeo_cost_of_living_index", "N/A")} (100=NYC)

{tugo_details if tugo_details else ""}

YOUR ROLE:
Provide personalized, actionable travel advice that EXPLICITLY references their stated preferences.

When making recommendations:
1. Always explain WHY it matches their profile (e.g., "Since you're a {persona} who {pref_text}, I recommend...")
2. Reference their priorities (they value: {priority_text})
3. Be specific: Mention actual places, restaurants, neighborhoods, costs
4. Consider their timeline: Plan within their {duration}-day window
5. Match their style: Align recommendations with their persona and swipe choices
6. **When discussing health, safety, or laws, reference the official TuGo information provided above**

Keep responses conversational, 250-400 words, and structure them well for readability."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]}
                  for m in st.session_state[chat_key][-6:]],  # Last 3 exchanges
                {"role": "user", "content": user_query}
            ],
            temperature=0.7,
            max_tokens=600  # Increased for more detailed responses
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Sorry, I couldn't process that. Error: {str(e)}"



def render_pdf_tab(country, data_manager):
    """PDF generation and download"""
    st.markdown("### 📄 Download Travel Guide")
    st.info("Generate a personalized PDF guide with all the information you need!")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Includes:**")
        st.markdown("""
        - ✅ Your match score & persona
        - ✅ Safety & health information
        - ✅ Cost of living index
        - ✅ Cultural highlights
        - ✅ Essential phrases in local language
        - ✅ Personalized travel tips
        """)
    
    with col2:
        if st.button("📥 Generate PDF", use_container_width=True, type="primary"):
            with st.spinner("Creating your guide..."):
                pdf_buffer = generate_country_pdf(country, data_manager)
                
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_buffer,
                    file_name=f"{country['country_name']}_travel_guide.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF ready!")


def safe_format_number(value, field_name=None):
    """Safely format a number, return 'N/A' if not numeric or missing"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 'N/A'
    
    # Handle string 'nan' or 'NaN'
    if isinstance(value, str):
        if value.lower() in ['nan', 'none', 'null', '']:
            return 'N/A'
        try:
            return f"{float(value):.0f}"
        except (ValueError, TypeError):
            return 'N/A'
    
    # Handle numeric types
    try:
        num_val = float(value)
        # Check if it's actually NaN
        if pd.isna(num_val):
            return 'N/A'
        return f"{num_val:.0f}"
    except (ValueError, TypeError):
        return 'N/A'

def get_pdf_ai_content(country):
    """
    Ask the OpenAI API for:
    - romanized translations of fixed phrases into the main local language
    - extra personalized tips for the PDF
    Returns (translations_dict, extra_tips_list).
    """
    try:
        client = OpenAI()  # uses OPENAI_API_KEY from env
        persona = st.session_state.get('selected_persona', 'Traveler')
        prefs = st.session_state.get('prefs', {})
        weights = st.session_state.get('weights', {})
        
        target_temp = prefs.get('target_temp')
        food_style = prefs.get('foodstyle')
        night_style = prefs.get('nightstyle')
        move_style = prefs.get('movestyle')
        
        top_priorities = sorted(
            [(k, v) for k, v in weights.items() if v > 0.10],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        priority_labels = [k.replace('_', ' ').title() for k, _ in top_priorities]
        
        # Build a compact traveler summary
        pref_bits = []
        if food_style:
            pref_bits.append(f"food_style={food_style}")
        if night_style:
            pref_bits.append(f"night_style={night_style}")
        if move_style:
            pref_bits.append(f"move_style={move_style}")
        if isinstance(target_temp, (int, float)):
            pref_bits.append(f"target_temp={target_temp}C")
        if priority_labels:
            pref_bits.append("priorities=" + ", ".join(priority_labels))
        
        traveler_summary = "; ".join(pref_bits) if pref_bits else "balanced preferences"
        
        local_language = (
            country.get('official_language')
            or country.get('language')
            or "the main local language of this country"
        )
        
        system_prompt = (
            "You are a translation and travel tips assistant. "
            "You MUST respond with ONLY valid JSON, no markdown formatting, no code blocks, no extra text. "
            "For translations, provide ONLY romanized/transliterated versions using Latin characters."
        )
        
        user_prompt = f"""Country: {country.get('country_name')}
Main language: {local_language}
Traveler persona: {persona}
Traveler profile: {traveler_summary}

1) Translate these 5 sentences from English into {local_language}.
   IMPORTANT: Return ONLY the romanized/transliterated version (no native script).
   For example, if translating to Arabic, return "Marhaba" (NOT "مرحبا").
   For Nepali, return "Namaste" (NOT "नमस्ते").
   For Russian, return "Zdravstvuyte" (NOT "Здравствуйте").
   For all languages, provide only the Latin/romanized version.

- "Hello!"
- "How are you?"
- "Thank you!"
- "My name is ..."
- "I am a poor student, how much does this cost?"

2) Create 3 short, practical travel tips tailored to this traveler and country.
Each tip must be one bullet-sized sentence, under 30 words.

Return ONLY this JSON structure with no markdown formatting:
{{
  "translations": {{
    "Hello!": "romanized version only",
    "How are you?": "romanized version only",
    "Thank you!": "romanized version only",
    "My name is ...": "romanized version only",
    "I am a poor student, how much does this cost?": "romanized version only"
  }},
  "extra_tips": [
    "tip 1",
    "tip 2",
    "tip 3"
  ]
}}"""
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        
        import json
        content = resp.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split('\n')
            lines = lines[1:]  # Remove first line (```json or ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line (```)
            content = '\n'.join(lines)
        
        data = json.loads(content)
        translations = data.get("translations", {})
        extra_tips = data.get("extra_tips", [])
        
        return translations, extra_tips
        
    except Exception as e:
        print(f"Translation API error: {e}")
        st.warning(f"⚠️ AI translations unavailable. Using English in PDF.")
        return {}, []


def generate_country_pdf(country, data_manager):
    """Generate PDF summary of country with extra AI-style content"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
    story = []

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=20,
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
    )

    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=6,
        spaceAfter=6,
        textColor=colors.HexColor('#1a237e'),
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
    )

    # ------------------------------------------------------------------
    # Title & meta
    # ------------------------------------------------------------------
    story.append(Paragraph(f"{country['country_name']}", title_style))

    persona = st.session_state.get('selected_persona', 'Traveler')
    score = country.get('final_score', 0) * 100
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))

    story.append(
        Paragraph(
            f"Personalized Guide for {persona} • Match Score: {score:.0f}% "
            f"• Travel Dates: {start_date} to {end_date}",
            subtitle_style,
        )
    )

    # ------------------------------------------------------------------
    # Quick Facts Table (existing)
    # ------------------------------------------------------------------
    story.append(Paragraph("Quick Facts", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))

    advisory_raw = country.get('tugo_advisory_state')
    advisory = str(advisory_raw) if advisory_raw is not None and pd.notna(advisory_raw) else 'N/A'

    temp_val = country.get('climate_avg_temp_c', 'N/A')
    if temp_val is not None and not (isinstance(temp_val, float) and pd.isna(temp_val)):
        try:
            climate_str = f"{float(temp_val):.0f}°C"
        except Exception:
            climate_str = 'N/A'
    else:
        climate_str = 'N/A'

    healthcare_val = safe_format_number(country.get('numbeo_healthcare_index'))
    if healthcare_val == 'N/A':
        for key in country.keys():
            if 'health' in key.lower():
                val = country.get(key)
                if val is not None and not pd.isna(val):
                    formatted = safe_format_number(val)
                    if formatted != 'N/A':
                        healthcare_val = formatted
                        break

    facts_data = [
        ['Safety Advisory', advisory[:80]],
        ['Climate', climate_str],
        ['UNESCO Sites', str(int(country.get('unesco_count', 0)))],
        ['Cost of Living (Index)', safe_format_number(country.get('numbeo_cost_of_living_index'))],
        ['Healthcare Index', healthcare_val],
    ]

    table = Table(facts_data, colWidths=[2.7 * inch, 3.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # Essential Phrases
    # ------------------------------------------------------------------
    story.append(Paragraph("Essential Phrases", section_header))

    translations, _ = get_pdf_ai_content(country)
    base_phrases = [
        "Hello!",
        "How are you?",
        "Thank you!",
        "My name is ...",
        "I am a poor student, how much does this cost?",
    ]

    # Display only romanized versions
    if translations:
        for eng in base_phrases:
            loc = translations.get(eng, eng)
            story.append(Paragraph(f"• {eng} – {loc}", bullet_style))
    else:
        # Fallback if no translations available
        story.append(Paragraph("• Consult a local phrasebook for essential phrases.", bullet_style))

    story.append(Spacer(1, 0.2 * inch))



    # ------------------------------------------------------------------
    # NEW SECTION 2: Tarot sentence (if available)
    # ------------------------------------------------------------------
    tarot_card = st.session_state.get('tarot_card', {})
    tarot_name = tarot_card.get('name')
    tarot_meaning = tarot_card.get('travel_meaning', '') or tarot_card.get('meaning', '')
    is_reversed = tarot_card.get('is_reversed', False)

    if tarot_name:
        orientation = "reversed" if is_reversed else "upright"
        story.append(Paragraph("Tarot Guidance", section_header))
        tarot_text = (
            f"Your trip is influenced by the card <b>{tarot_name}</b> ({orientation}). "
            f"In a travel context, this suggests: {tarot_meaning}"
        )
        story.append(Paragraph(tarot_text, bullet_style))
        story.append(Spacer(1, 0.2 * inch))

    # ------------------------------------------------------------------
    # NEW SECTION 3: Personalized quick tips based on preferences
    # ------------------------------------------------------------------
    story.append(Paragraph("Personalized Travel Tips", section_header))

    prefs = st.session_state.get('prefs', {})
    weights = st.session_state.get('weights', {})

    target_temp = prefs.get('target_temp')
    food_style = prefs.get('foodstyle')
    night_style = prefs.get('nightstyle')
    move_style = prefs.get('movestyle')

    top_priorities = sorted(
        [(k, v) for k, v in weights.items() if v > 0.10],
        key=lambda x: x[1],
        reverse=True,
    )[:3]
    priority_labels = [k.replace('_', ' ').title() for k, _ in top_priorities]

    tips = []

    # Budget / cost focused
    if 'Cost' in " ".join(priority_labels) or 'Budget' in persona:
        tips.append(
            "Focus on affordable neighborhoods, street food, and free cultural sites. "
            "Use local public transport instead of taxis where it feels safe."
        )

    # Culture / UNESCO
    if any('Culture' in p or 'Unesco' in p for p in priority_labels):
        tips.append(
            "Plan at least one day around major museums or UNESCO sites. "
            "Book tickets in advance to avoid queues and peak-hour crowds."
        )

    # Air quality / calm
    if any('Clean Air' in p or 'Calm' in p for p in priority_labels):
        tips.append(
            "Look for parks, coastal areas, or hill regions to balance busy city days with quiet nature time."
        )

    # Food style
    if food_style == 'eatout':
        tips.append(
            "Since you enjoy eating out, mark a few highly rated local restaurants and one special place "
            "for a 'treat yourself' dinner."
        )
    elif food_style == 'cook':
        tips.append(
            "You prefer cooking, so search for accommodation near supermarkets or markets and check if the "
            "kitchen is well equipped."
        )

    # Night style
    if night_style == 'party':
        tips.append(
            "Check local nightlife districts and always plan a safe way back to your accommodation before you go out."
        )
    elif night_style == 'chill':
        tips.append(
            "Choose areas with cafés, promenades or quiet bars where you can relax in the evening without heavy crowds."
        )

    # Movement style
    if move_style == 'walk':
        tips.append(
            "Pick compact neighborhoods and pack comfortable shoes, as you will likely explore a lot on foot."
        )

    # Climate preference
    if isinstance(target_temp, (int, float)):
        if target_temp < 20:
            tips.append(
                "Pack layers and a light jacket, especially for evenings or higher-altitude excursions."
            )
        elif target_temp > 26:
            tips.append(
                "Bring light, breathable clothing, sunscreen, and a refillable water bottle to handle the warmth."
            )

    # Fallback if nothing detected
    if not tips:
        tips.append(
            "Balance your itinerary between must-see highlights and slower days so you return energized instead of exhausted."
        )
    
     # Add extra AI-generated tips (if any)
    _, extra_tips = get_pdf_ai_content(country)
    for t in extra_tips:
        if isinstance(t, str) and t.strip():
            tips.append(t.strip())

    # Single bullet per item – ListFlowable provides the bullet
    tip_paragraphs = [Paragraph(t, bullet_style) for t in tips]
    story.append(ListFlowable(tip_paragraphs, bulletType='bullet', leftIndent=12))
    story.append(Spacer(1, 0.3 * inch))

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"Generated by Your Next Adventure • {datetime.date.today()}",
            subtitle_style,
        )
    )

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

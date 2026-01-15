"""
Country Overview Module - Visual dashboard, chatbot, and PDF export
"""
import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors


def render_country_overview(country, data_manager, openai_client, amadeus, amadeus_api_key, amadeus_api_secret):
    """
    Main entry point for country overview page
    """
    # Hero Section
    render_hero_section(country)
    
    # Quick Stats
    render_quick_stats(country)
    
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "💰 Budget Planner",
        "✈️ Book Flights",
        "🤖 AI Assistant", 
        "📄 Download PDF"
    ])
    
    with tab1:
        render_overview_tab(country, data_manager)
    
    with tab2:
        render_budget_tab(country, data_manager)
    
    with tab3:
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
            image_urls=(country.get('img1'), country.get('img2'), country.get('img3')),
            key_prefix=f"fs_{iso3}"
        )
    
    with tab4:
        render_chatbot_tab(country, openai_client)
    
    with tab5:
        render_pdf_tab(country, data_manager)


def render_hero_section(country):
    """Hero section with country name and image"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"# 🌍 {country['country_name']}")
        score = country.get('final_score', 0) * 100
        st.caption(f"Your personalized travel guide • Match Score: **{score:.0f}%**")
    
    with col2:
        imgs = [country.get('img1'), country.get('img2'), country.get('img3')]
        imgs = [x for x in imgs if x]
        if imgs:
            st.image(imgs[0], use_container_width=True)


def render_quick_stats(country):
    """Quick metric cards at the top"""
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        # Get safety score (1 = safest, 3 = most dangerous)
        safety_score = country.get('tugo_score')
        # ✅ GET ADVISORY FIRST - before any comparisons
        advisory = country.get('tugo_advisory_state', 'Unknown')
        advisory = str(advisory) if pd.notna(advisory) else 'Unknown'
        
        # Option A: Convert to int for comparison
        if safety_score is not None and pd.notna(safety_score):
            safety_score = int(safety_score)
        
        if safety_score == 1:
            emoji = "✅"
            safety_desc = "Safe - Exercise normal precautions."
        elif safety_score == 2:
            emoji = "⚠️"
            safety_desc = "Caution - Exercise increased caution due to risks."
        elif safety_score == 3:
            emoji = "🚨"
            safety_desc = "High Risk - Reconsider travel due to serious safety concerns."
        else:
            # Fallback to text-based logic if score not available
            if "exercise normal" in advisory.lower():
                emoji = "✅"
                safety_desc = "Safe - Exercise normal precautions."
            elif "high degree" in advisory.lower() or "increased" in advisory.lower():
                emoji = "⚠️"
                safety_desc = "Caution - Exercise increased caution due to risks."
            else:
                emoji = "🚨"
                safety_desc = "High Risk - Reconsider travel due to serious safety concerns."
        
        st.metric("🛡️ Safety", emoji, help=f"{safety_desc}\n\nFull Advisory: {advisory}")
    
    with m2:
        temp = country.get('climate_avg_temp_c')
        if temp and pd.notna(temp):
            st.metric("🌡️ Climate", f"{temp:.0f}°C")
        else:
            st.metric("🌡️ Climate", "N/A")
    
    with m3:
        unesco = int(country.get('unesco_count', 0))
        st.metric("🏛️ UNESCO Sites", f"{unesco}")
    
    with m4:
        flight = country.get('flight_price')
        if flight and pd.notna(flight):
            symbol = st.session_state.get('currency_symbol', '€')
            rate = st.session_state.get('currency_rate', 1.0)
            price = float(flight) * rate
            st.metric("✈️ Flight", f"{symbol}{price:.0f}")
        else:
            st.metric("✈️ Flight", "N/A")




def render_overview_tab(country, data_manager):
    """Main overview with visual cards and personalized info"""
    
    # Why This Match?
    st.markdown("### 🎯 Why This Match?")
    render_match_reasons(country)
    
    st.markdown("---")
    
    # Visual Highlight Cards
    st.markdown("### ✨ Key Highlights")
    render_highlight_cards(country)
    
    st.markdown("---")
    
    # Quick Safety & Health Info (no tables!)
    st.markdown("### 📋 Quick Reference")
    render_quick_reference(country, data_manager)


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
    prefs = st.session_state.get('prefs', {})
    target_temp = prefs.get('target_temp', 25)
    actual_temp = country.get('climate_avg_temp_c')
    if actual_temp and abs(target_temp - actual_temp) < 5:
        reasons.append(f"🌡️ **Perfect weather** - {actual_temp:.0f}°C matches your preference")
    
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
            st.markdown("#### 💵 Budget")
            col_idx = country.get('numbeo_cost_of_living_index', 50)
            # Invert for display: lower cost = higher bar
            budget_score = max(0, 150 - col_idx) / 150
            st.progress(min(budget_score, 1.0))
            st.caption(f"Cost of living: {col_idx:.0f} (100 = NYC)")
            if col_idx < 60:
                st.success("💰 Very affordable!")
            elif col_idx < 90:
                st.info("💵 Moderate pricing")
            else:
                st.warning("💸 Premium destination")
    
    with col2:
        with st.container(border=True):
            st.markdown("#### 🏥 Healthcare")
            
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
            st.markdown("#### 🌬️ Air Quality")
            pol = country.get('numbeo_pollution_index', 50)
            air_score = max(0, 100 - pol)
            st.progress(air_score/100)
            st.caption(f"Air quality: {air_score:.0f}/100")
            if air_score > 70:
                st.success("🌿 Fresh air!")
            elif air_score > 50:
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
        st.success("Use the Budget Planner and Flight Search tabs to plan your trip!")




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


def render_chatbot_tab(country, openai_client):
    """AI-powered trip planning chatbot"""
    st.markdown("### 🤖 Your AI Travel Assistant")
    
    # ✅ NEW: Highlight personalization
    persona = st.session_state.get('selected_persona', 'Traveler')
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))
    
    st.info(f"✨ **Personalized for you!** This assistant knows your travel style (*{persona}*), dates ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}), and preferences to give you tailored recommendations.")
    
    st.caption(f"Ask me anything about planning your trip to {country['country_name']}!")
    
    # Initialize chat history per country
    chat_key = f"chat_{country['iso3']}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
        # Welcome message
        duration = (end_date - start_date).days
        st.session_state[chat_key].append({
            "role": "assistant",
            "content": f"👋 Hi! I'm your personalized AI guide for **{country['country_name']}**!\n\n"
                      f"I already know you're a **{persona}** traveling for **{duration} days** "
                      f"from **{start_date.strftime('%b %d')} to {end_date.strftime('%b %d')}**. "
                      f"I've studied your preferences and can provide tailored advice on:\n\n"
                      "- 📍 Day-by-day itineraries matched to your interests\n"
                      "- 🍽️ Restaurants & attractions fitting your budget\n"
                      "- 🚇 Transportation tips & local navigation\n"
                      "- 💡 Safety advice & cultural customs\n\n"
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
                response = get_ai_travel_response(prompt, country, openai_client, chat_key)
                st.markdown(response)
        
        st.session_state[chat_key].append({"role": "assistant", "content": response})
        st.rerun()



def get_ai_travel_response(user_query, country, openai_client, chat_key):
    """Generate AI response with country context"""
    persona = st.session_state.get('selected_persona', 'Traveler')
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))
    duration = (end_date - start_date).days
    
    system_prompt = f"""You are an expert travel assistant helping plan a trip to {country['country_name']}.

User Profile:
- Traveler Type: {persona}
- Trip Duration: {duration} days ({start_date} to {end_date})
- Safety Advisory: {country.get('tugo_advisory_state', 'Unknown')}
- Budget Level: {'Budget-conscious' if 'Budget' in persona else 'Flexible'}

Provide practical, personalized advice. Include:
- Specific recommendations (places, restaurants, activities)
- Practical tips (transportation, costs, timing)
- Safety & cultural considerations
- Day-by-day itinerary suggestions when asked

Keep responses concise (200-300 words) and actionable. Use emojis for readability."""

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
            max_tokens=500
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
        - ✅ Budget breakdown
        - ✅ Cultural highlights
        - ✅ Travel tips
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



def generate_country_pdf(country, data_manager):
    """Generate PDF summary of country"""
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
        spaceAfter=30,
    )
    
    # Title
    story.append(Paragraph(f"{country['country_name']}", title_style))
    
    # Metadata
    persona = st.session_state.get('selected_persona', 'Traveler')
    score = country.get('final_score', 0) * 100
    start_date = st.session_state.get('start_date', datetime.date.today())
    end_date = st.session_state.get('end_date', start_date + datetime.timedelta(days=7))
    
    story.append(Paragraph(
        f"Personalized Guide for {persona} • Match Score: {score:.0f}%<br/>"
        f"Travel Dates: {start_date} to {end_date}",
        subtitle_style
    ))
    
    # Quick Facts Table
    story.append(Paragraph("<b>Quick Facts</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    advisory = str(country.get('tugo_advisory_state', 'N/A')) if pd.notna(country.get('tugo_advisory_state')) else 'N/A'
    
    # ✅ FIXED: Better handling for all fields
    temp_val = country.get('climate_avg_temp_c', 'N/A')
    if pd.notna(temp_val):
        climate_str = f"{float(temp_val):.0f}°C"
    else:
        climate_str = 'N/A'
    
    # ✅ CRITICAL FIX: Try all possible healthcare index field names
    healthcare_val = safe_format_number(country.get('numbeo_healthcare_index'))
    
    # If that didn't work, debug and try alternatives
    if healthcare_val == 'N/A':
        # Print all fields containing 'health' or 'healthcare' for debugging
        for key in country.keys():
            if 'health' in key.lower():
                val = country.get(key)
                if val is not None and not pd.isna(val):
                    formatted = safe_format_number(val)
                    if formatted != 'N/A':
                        healthcare_val = formatted
                        break
    
    facts_data = [
        ['Safety Advisory', advisory[:50]],
        ['Climate', climate_str],
        ['UNESCO Sites', str(int(country.get('unesco_count', 0)))],
        ['Cost of Living', safe_format_number(country.get('numbeo_cost_of_living_index'))],
        ['Healthcare Index', healthcare_val],
    ]
    
    table = Table(facts_data, colWidths=[2.5*inch, 4*inch])
    table.setStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f5f7fa')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ])
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        f"Generated by Your Next Adventure • {datetime.date.today()}",
        subtitle_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

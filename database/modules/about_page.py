# modules/about_page.py
import streamlit as st
import os
import datetime


def _badge(text: str, icon: str = "✅"):
    st.markdown(
        f"""
        <div style="
            display:inline-flex; align-items:center; gap:8px;
            padding:6px 12px; border-radius:999px;
            background: rgba(25, 35, 55, 0.75);
            border: 1px solid rgba(120, 170, 240, 0.35);
            box-shadow: 0 6px 18px rgba(0,0,0,0.25);
            font-weight:600; font-size:0.95rem;
        ">
            <span style="font-size:1.05rem;">{icon}</span>
            <span>{text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_title(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div style="
            margin-top: 0.25rem;
            padding: 18px 18px 14px 18px;
            border-radius: 16px;
            background: rgba(15, 20, 40, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(18px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        ">
            <div style="font-size:1.9rem; font-weight:800; letter-spacing:-0.5px;">
                {title}
            </div>
            {f"<div style='margin-top:6px; color: rgba(255,255,255,0.78); font-size:1.05rem; line-height:1.4;'>{subtitle}</div>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _mini_card(title: str, body_html: str, icon: str = "📌"):
    # IMPORTANT: body_html should be HTML (not markdown) to avoid the </div> artifact.
    st.markdown(
        f"""
        <div style="
            border-radius: 16px;
            padding: 16px 16px 14px 16px;
            background: rgba(25, 35, 55, 0.45);
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: 0 10px 26px rgba(0,0,0,0.22);
            backdrop-filter: blur(16px);
            height: 100%;
        ">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <div style="font-size:1.35rem;">{icon}</div>
                <div style="font-size:1.1rem; font-weight:750;">{title}</div>
            </div>
            <div style="color: rgba(255,255,255,0.82); font-size:0.98rem; line-height:1.55;">
                {body_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _html_list(items):
    lis = "\n".join([f"<li>{it}</li>" for it in items])
    return f"<ul style='margin-top:0; line-height:1.9;'>{lis}</ul>"


def _req_block(title: str, lines):
    st.markdown(
        f"""
        <div style="
            border-radius: 16px;
            padding: 14px 14px 12px 14px;
            background: rgba(10, 15, 30, 0.30);
            border: 1px solid rgba(255,255,255,0.10);
            margin-bottom: 12px;
        ">
            <div style="font-size:1.05rem; font-weight:800; margin-bottom:10px; opacity:0.95;">
                {title}
            </div>
            <pre style="
                margin:0;
                padding: 12px;
                border-radius: 12px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                overflow-x:auto;
                font-size: 0.95rem;
                line-height: 1.55;
            ">{chr(10).join(lines)}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_about_page():
    _section_title(
        "ℹ️ Pathfind — About",
        "A personalized travel planner dashboard — documentation for workflow, data, scoring, modules, and integrations.",
    )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        _badge("Step-based flow", "🧭")
    with c2:
        _badge("Unified SQLite DB", "🗄️")
    with c3:
        _badge("Interpretable scoring", "🧠")
    with c4:
        _badge("Seeds for diversity", "🎲")

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    tabs = st.tabs(
        [
            "🌍 Overview",
            "🧭 Workflow",
            "📊 Data & Sources",
            "🧠 Scoring",
            "💸 Cost Estimator",
            "✈️ Flight Search",
            "🗺️ Path Finder",
            "🧾 Export / PDF",
            "🔐 APIs & Security",
            "🧰 Requirements",
            "🛡️ Privacy",
            "🏛️ Impressum",
        ]
    )

    # ------------------------------------------------------------
    # OVERVIEW
    # ------------------------------------------------------------
    with tabs[0]:
        _section_title(
            "What is Pathfind?",
            "Pathfind helps users discover travel destinations that match their preferences — with explainable ranking and rich country-level details.",
        )

        st.markdown(
            """
**Pathfind** is an interactive Streamlit dashboard that supports users in finding travel destinations that match their personal preferences.  
The system combines country-level datasets (cost of living, quality of life, safety, climate, equality indicators) with user input (persona, swipes, filters) to compute an interpretable destination ranking and provide country-level details including flight estimates and trip + route planning modules.
            """
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "What you get",
                _html_list(
                    [
                        "A ranked list of destinations (Top Matches)",
                        "Category-based score explanations (\"Peek behind the score\")",
                        "Country dashboard with deeper info",
                        "Cost Estimator (Numbeo items + trip budgeting)",
                        "Flight context and optional live flight search flow",
                        "Trip planning / route planning support for the selected destination",
                        "Optional calendar export via Google OAuth",
                    ]
                ),
                icon="🎯",
            )
        with b:
            _mini_card(
                "What this is not",
                _html_list(
                    [
                        "Not a guarantee of safety, pricing, or availability",
                        "Not a replacement for official advisories",
                        "Not a live booking engine by default (estimates can differ from market prices)",
                        "Not a city-level model — many inputs are country-level averages",
                    ]
                ),
                icon="⚠️",
            )

    # ------------------------------------------------------------
    # WORKFLOW
    # ------------------------------------------------------------
    with tabs[1]:
        _section_title("✅ How Pathfind Works (Step Flow)")

        st.markdown(
            """
The app is structured as a step-based flow using `st.session_state["step"]`.  
A typical user run looks like this:
            """
        )

        with st.expander("Step 1 — Basic Setup (Origin, Dates, LGBTQ+ Filter)", expanded=True):
            st.markdown(
                """
Users select:
- starting airport (currently **Germany/FRA** or **USA/ATL**),
- vacation dates,
- optional **LGBTQ+ Safe Travel Filter**.

This step initializes a **new run**, including generating **new random seeds** used for controlled randomness in later stages.
                """
            )

        with st.expander("Step 2 — Persona Selector", expanded=False):
            st.markdown(
                """
Users choose a persona profile (e.g., budget traveler, luxury, explorer).  
Personas set structured default weights across decision dimensions.
                """
            )

        with st.expander("Step 3 — Swipe Questionnaire (Randomized Mini-Run)", expanded=False):
            st.markdown(
                """
Pathfind uses a compact swipe flow: the app draws **6 random swipe cards per run**.
- The selection is randomized but **seed-controlled** so it stays consistent within the same run.
- Each swipe updates weights and preferences (e.g., weather target temperature, cost emphasis, clean air).
                """
            )

        with st.expander("Step 4 — Tarot (Optional)", expanded=False):
            st.markdown(
                """
Users can optionally draw a Tarot card:
- Tarot card draw comes from the **Roxy API**.
- The resulting card name + orientation is matched against a mapping table (**`tarot_countries`**) in the project database.

If activated, Tarot-linked countries receive a controlled boost (via the **`astro`** weight).
                """
            )

        with st.expander("Step 5 — Ban List (Optional)", expanded=False):
            st.markdown(
                """
Users can exclude entire world regions.
Each region maps to a fixed ISO3 list (**`REGION_TO_ISO3`**).  
All matching countries are removed before scoring.
                """
            )

        with st.expander("Step 6 — Matching Results + Explanation", expanded=False):
            st.markdown(
                """
The system loads the base dataset, applies filters, computes sub-scores and a final score, and displays the top destinations.
Each result contains a “Peek behind the score” explanation showing category contributions.
                """
            )

        with st.expander("Step 7 — Country Dashboard (Details + Planning)", expanded=False):
            st.markdown(
                """
The Country Dashboard provides:
- country overview and contextual info,
- trip planning module,
- Path Finder route planning support,
- cost estimator breakdown (optional),
- optional deep dives and generated explanation content.
                """
            )

        with st.expander("Step 8–9 — Booking + Confirmation (Flights + Calendar Export)", expanded=False):
            st.markdown(
                """
Users can proceed to flight booking and optionally export trip information into **Google Calendar** via OAuth.
                """
            )

        st.markdown("---")
        _mini_card(
            "Run behavior (freshness)",
            _html_list(
                [
                    "During a run, seeds keep randomized components stable (repeatable UI within the run).",
                    "A new run (Start Over + Step 1) generates fresh seeds for variety and new outcomes.",
                ]
            ),
            icon="🎲",
        )

    # ------------------------------------------------------------
    # DATA & SOURCES
    # ------------------------------------------------------------
    with tabs[2]:
        _section_title("📊 Data Sources & Database Structure")

        st.markdown(
            """
All structured country-level data is stored in a unified SQLite database (**`unified_country_database.db`**), which serves as the single source of truth.
            """
        )

        st.markdown("### Key tables (core)")
        st.markdown(
            """
- **countries**: ISO codes, country name, images, advisory states  
- **numbeo_indices**: cost of living, rent, groceries, restaurant, purchasing power, QoL, healthcare, pollution  
- **climate_monthly**: average temperatures  
- **unesco_heritage_sites**: UNESCO counts per country  
- **airports**: airport mapping and metadata  
- **flight_costs**: flight estimate samples between origin and major destination airports  
- **equality_index**: equality scores used for LGBTQ+ filter  
- **tugo_safety, tugo_health, tugo_entry**: travel guidance detail tables  
- **tarot_countries**: tarot card mapping to countries + travel meanings  
            """
        )

        st.markdown("### How the base dataset is assembled")
        st.markdown(
            """
Pathfind assembles a country-level candidate dataset by joining:
- `countries` with Numbeo indices, climate averages, UNESCO counts, and equality indicators
- and (optionally) flight estimates from `flight_costs` via major airports  
After joins, the dataset is deduplicated to one row per country (ISO3), preferring rows with fewer missing values.
            """
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        _mini_card(
            "Data providers & credits",
            _html_list(
                [
                    "<b>Numbeo</b> — cost of living indices + item-level prices (scoring + cost estimator)",
                    "<b>Tugo</b> — travel advisories (safety / health / entry guidance)",
                    "<b>UNESCO</b> — World Heritage Sites (counts and examples)",
                    "<b>Climate data</b> — monthly average temperatures (aggregated in DB)",
                    "<b>Amadeus</b> — flight search and itinerary/price signals",
                    "<b>Google APIs</b> — calendar export (OAuth) + maps/routing support",
                    "<b>Roxy API</b> — tarot card draw (optional, playful extension)",
                    "<b>Serper</b> — search-based enrichment for routing / POIs (if enabled)",
                    "<b>OpenAI</b> — LLM-generated explanations in the country dashboard (if enabled)",
                ]
            ),
            icon="🙏",
        )

        _mini_card(
            "Important note",
            "Some signals are country-level averages. They provide guidance but cannot capture city-level or individual-level variation.",
            icon="ℹ️",
        )

    # ------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------
    with tabs[3]:
        _section_title("🧠 Scoring & Matching Logic")

        st.markdown(
            """
Pathfind computes interpretable sub-scores in the range **0–1** and combines them into a final score using user-defined weights.
            """
        )

        with st.expander("Normalization (winsorize + min-max)", expanded=True):
            st.markdown(
                """
For each numeric indicator:
- values are **winsorized** (5th–95th percentile) to reduce outlier impact  
- then **min-max normalized** to 0–1  

Examples:
- lower cost-of-living → higher `cost_score`  
- lower pollution → higher `clean_air_score`  
- closer to preferred temperature → higher `weather_score`
                """
            )

        with st.expander("Weighting (0–100, normalized to sum = 100)", expanded=False):
            st.markdown(
                """
Weights come from persona defaults + swipe adjustments.  
Weights are normalized so they always sum to **100**.
                """
            )

        with st.expander("Final Score (no forced 100% top rank)", expanded=False):
            st.markdown(
                """
`final_score_raw` is computed as a weighted sum of category scores.  
The final score is clipped into **0–1** — Pathfind does **not** rescale scores to force the #1 destination to become “100%”.
                """
            )

        with st.expander("🎲 Controlled randomness (seeds)", expanded=False):
            st.markdown(
                """
Pathfind uses controlled randomness to diversify close outcomes:
- `hidden_gem_score`: combines “low UNESCO” with stable noise based on `gem_seed`
- swipe card selection: randomized but stable within run using `jitter_seed`
- `jitter_score`: small stable noise to break ties, based on `jitter_seed`

New seeds are generated at the start of each new run (after Step 1).  
Pressing “Start Over” clears the session state entirely, ensuring a fresh run.
                """
            )

    # ------------------------------------------------------------
    # COST ESTIMATOR
    # ------------------------------------------------------------
    with tabs[4]:
        _section_title("💸 Cost Estimator (Numbeo-driven trip budgeting)")

        st.markdown(
            """
Pathfind includes a **Cost Estimator** module that translates country-level price data into a practical trip budget estimate.

It uses Numbeo item prices and scales them to:
- trip length (days / weeks),
- group size (adults / kids),
- item frequency (per day / week / month),
- optional currency conversion (based on origin).
            """
        )

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "What it outputs",
                _html_list(
                    [
                        "Estimated totals across cost categories",
                        "Item-level breakdown with transparent assumptions",
                        "Scaled results by trip duration and group size",
                    ]
                ),
                icon="🧾",
            )
        with b:
            _mini_card(
                "Interpretation",
                _html_list(
                    [
                        "Uses averages; real costs vary by region and season",
                        "Travel style and accommodation dominate real budgets",
                    ]
                ),
                icon="🔍",
            )

        st.info("Cost estimates are planning guidance (not a guarantee).")

    # ------------------------------------------------------------
    # FLIGHT SEARCH
    # ------------------------------------------------------------
    with tabs[5]:
        _section_title("✈️ Flight Search (Estimates + optional live search flow)")

        st.markdown(
            """
Pathfind supports flights on two levels:
1) **Fast DB-based flight estimates** (quick context in rankings)  
2) **Optional live flight search flow** (Amadeus) once users shortlist destinations
            """
        )

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "Level 1 — Flight Estimates (Database)",
                _html_list(
                    [
                        "Uses `flight_costs` joined via major airports per country",
                        "Provides a fast reference signal (available offline)",
                        "Shown in results as a rough context for affordability",
                    ]
                ),
                icon="⚡",
            )
        with b:
            _mini_card(
                "Level 2 — Live Flight Search (Amadeus)",
                _html_list(
                    [
                        "Triggered in booking steps once user proceeds",
                        "Uses origin, destination airport mapping, travel dates",
                        "Returns itineraries with carrier, layovers, timing, and price",
                    ]
                ),
                icon="🛰️",
            )

        st.warning("Flight prices and availability can change quickly and may differ from estimates.")

    # ------------------------------------------------------------
    # PATH FINDER / ROUTE PLANNER
    # ------------------------------------------------------------
    with tabs[6]:
        _section_title("🗺️ Path Finder (Route Planner / Trip Planner)")

        st.markdown(
            """
Pathfind includes a route & trip planning component for the selected destination.  
It is designed to support exploration and itinerary-building inside the dashboard (not to replace a full navigation app).
            """
        )

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "What it does",
                _html_list(
                    [
                        "Visualizes relevant locations (POIs) on a map",
                        "Supports simple itinerary building / ordering logic",
                        "Helps structure a trip around user interests",
                    ]
                ),
                icon="🧭",
            )
        with b:
            _mini_card(
                "How it works (typical)",
                _html_list(
                    [
                        "Map rendering with Folium + streamlit-folium",
                        "Geo utilities with geopy / geonamescache / pycountry",
                        "Optional: Google Maps API for routing and map enrichment",
                        "Optional: Serper for search-based POI enrichment",
                        "Optional: polyline for route geometry visualization",
                    ]
                ),
                icon="🧩",
            )

        st.info("Routing is approximate depending on enabled providers and available data.")

    # ------------------------------------------------------------
    # EXPORT / PDF
    # ------------------------------------------------------------
    with tabs[7]:
        _section_title("🧾 Export / PDF")

        st.markdown(
            """
Pathfind can export key results for offline use (planning, sharing, printing).  
Typical export content includes:
- top matches + match scores,
- category breakdown (“Peek behind the score”),
- selected country dashboard highlights,
- flight context,
- trip planner output,
- cost estimator breakdown.
            """
        )

        st.warning("Exports never include API keys or secret credentials.")

    # ------------------------------------------------------------
    # APIs & Security
    # ------------------------------------------------------------
    with tabs[8]:
        _section_title("🔐 APIs, Environment Variables & Security")

        st.markdown(
            """
Pathfind integrates multiple external services:
- **Numbeo API** — indices + item prices for scoring and the cost estimator  
- **Tugo** — travel advisory data (safety / health / entry guidance)  
- **UNESCO** — world heritage site data (counts + examples)  
- **Amadeus API** — flight search and itinerary/price signals  
- **Google APIs** — calendar export (OAuth) and optional maps/routing support  
- **Serper API** — optional search enrichment for route planning  
- **OpenAI API** — optional LLM-based country explanations  
- **Roxy Tarot API** — optional tarot card draw  

All credentials are loaded via `.env` environment variables and should never be committed to a public repository.
            """
        )

        st.markdown("### .env.example (template — no secrets)")
        env_example = """AMADEUS_API_KEY=
AMADEUS_API_SECRET=
OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_MAPS_API_KEY=
SERPER_API_KEY=
ROXY_API_KEY=
NUMBEO_API_KEY=
"""
        st.code(env_example, language="bash")
        st.caption("Copy this into a `.env` file locally and fill in your keys. Never commit `.env`.")

        st.markdown("### Recommended repository setup")
        st.code(
            """# .gitignore
.env
__pycache__/
*.pyc
""",
            language="bash",
        )

    # ------------------------------------------------------------
    # REQUIREMENTS
    # ------------------------------------------------------------
    with tabs[9]:
        _section_title("🧰 Requirements (Python packages)")

        st.markdown(
            """
These packages are required to run **Pathfind**.  
They are typically stored in `requirements.txt` and installed via `pip install -r requirements.txt`.
            """
        )

        core = [
            "streamlit==1.52.2",
            "pandas==2.3.3",
            "python-dotenv==1.2.1",
        ]
        apis = [
            "openai==2.15.0",
            "requests==2.32.5",
            "google-api-python-client==2.187.0",
            "google-auth-oauthlib==1.2.3",
        ]
        geo = [
            "folium==0.20.0",
            "streamlit-folium==0.26.1",
            "geopy==2.4.1",
            "geonamescache==3.0.0",
            "polyline==2.0.4",
            "pycountry==24.6.1",
        ]
        export = [
            "reportlab==4.4.9",
        ]
        optional = [
            "protobuf==3.20.3",
        ]

        _req_block("Core", core)
        _req_block("APIs", apis)
        _req_block("Geo / Travel", geo)
        _req_block("Export", export)
        _req_block("Optional", optional)

    # ------------------------------------------------------------
    # PRIVACY / LIMITATIONS
    # ------------------------------------------------------------
    with tabs[10]:
        _section_title("🛡️ Privacy & Limitations")

        st.markdown(
            """
- Pathfind does **not** permanently store personal data.  
- User preferences exist only in **Streamlit session state**.  
- Safety and equality indicators provide data-based guidance only and cannot guarantee individual outcomes.  
- Flight prices are estimates or availability-dependent API results and may differ from market prices.  
            """
        )

        st.markdown("### Practical limitations (examples)")
        st.markdown(
            """
- Country-level averages hide regional differences (city vs countryside).  
- Cost estimates depend heavily on travel style and accommodation choices.  
- Advisories and equality indicators can change over time.  
            """
        )

    # ------------------------------------------------------------
    # IMPRESSUM
    # ------------------------------------------------------------
    with tabs[11]:
        _section_title("🏛️ Impressum / Project Context")

        st.markdown(
            """
This dashboard was developed as part of a **university group project**.  
It is intended for **research, learning, and demonstration purposes**.
            """
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        today = datetime.date.today().strftime("%Y-%m-%d")
        _mini_card(
            "Project metadata",
            _html_list(
                [
                    "Project: <b>Pathfind</b>",
                    "Type: University Group Project",
                    f"Last rendered: <b>{today}</b>",
                ]
            ),
            icon="📚",
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.caption("If deployed publicly, consider adding contact details and a short legal disclaimer depending on requirements.")


# Optional: allow quick standalone testing
# streamlit run modules/about_page.py
if __name__ == "__main__":
    render_about_page()

# modules/about_page.py
import streamlit as st
import os
import datetime


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


def _mini_card(title: str, body_html: str):
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
            <div style="font-size:1.1rem; font-weight:750; margin-bottom:8px;">
                {title}
            </div>
            <div style="color: rgba(255,255,255,0.82); font-size:0.98rem; line-height:1.55;">
                {body_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _html_list(items):
    lis = "\n".join([f"<li>{it.replace(chr(10), '<br>').replace('  ', '&nbsp;&nbsp;')}</li>" for it in items])
    return f"<ul style='margin-top:0; line-height:1.9;'>{lis}</ul>"


# Kept from old draft (even if not used anymore) to avoid breaking anything if you re-add later.
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
        "Pathfind — About",
        "A live, interactive travel planner dashboard — documentation for workflow, data, scoring, modules, and integrations.",
    )
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
    
    tabs = st.tabs(
        [
            "Overview",
            "Workflow",
            "Data & Sources",
            "Scoring",
            "Modules",
            "What makes Pathfind special",
            "Impressum",
        ]
    )

    # ------------------------------------------------------------
    # OVERVIEW
    # ------------------------------------------------------------
    with tabs[0]:
        _section_title(
            "What is Pathfind?",
            "A live and interactive travel planning dashboard with explainable ranking and integrated planning tools.",
        )

        st.markdown(
            """
**Pathfind is a live and interactive Streamlit dashboard** that helps users discover travel destinations that match their preferences.  
Users can explore destinations by dynamically adjusting profiles, sliders, filters, and constraints — and the ranking updates immediately as the system recomputes scores.

Pathfind is **interactive** because it works like a guided exploration or mini-game: users can select personas, answer swipe questions, tune preferences, and (optionally) interact with chatbot features for questions and planning.

Pathfind is **live** because selected components rely on live API calls (e.g., flight search, routing, interactive planning, Visa Requirements), and because parts of the underlying database contain regularly updated snapshots of external sources (e.g., travel safety and entry information). The system is therefore a hybrid of curated database signals and live services.

Pathfind can also optionally check **visa requirements** (powered by Travel Buddy) by matching the user’s selected nationality against destination-specific rules.
This feature integrates visa information directly into the destination overview and planning flow.
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
                        "Transparent score explanations (\"Peek behind the score\")",
                        "Country dashboard with contextual travel information",
                        "Cost Estimator for trip budgeting (item-level prices)",
                        "Flight context and optional live flight search flow",
                        "Trip Planner for itinerary building and routing support",
                        "Optional calendar export",
                        "Optional chatbot interaction for Q&A, explanations, and planning",
                        "Optional export/summary as PDF",
                    ]
                ),
            )
        with b:
            _mini_card(
                "What this is not",
                _html_list(
                    [
                        "Not a guarantee of safety, pricing, or availability",
                        "Not a replacement for official advisories",
                        "Not a pure booking engine (estimates can differ from market prices)",
                        "Not a city-level model — many inputs are country-level averages",
                    ]
                ),
            )

    # ------------------------------------------------------------
    # WORKFLOW
    # ------------------------------------------------------------
    with tabs[1]:
        _section_title("Workflow", "How users move through Pathfind")

        st.markdown(
            """
The app is structured as a step-based flow using `st.session_state["step"]`.  
A typical user run looks like this:
            """
        )

        with st.expander("Step 1 — Basic Setup (Origin, Dates, Filters)", expanded=True):
            st.markdown(
                """
- Users select origin and travel dates and can activate optional filters (e.g., safety-related indicators).
- Optionally select nationality for visa requirement checks (Travel Buddy).  

This step initializes a new run (including fresh randomized elements used later in the flow).
                """
            )

        with st.expander("Step 2 — Persona Selector", expanded=False):
            st.markdown(
                """
Users choose a persona (e.g., budget, explorer, comfort-oriented).  
Personas set structured default weights across decision dimensions.
                """
            )

        with st.expander("Step 3 — Swipe Interaction (Compact Preference Refinement)", expanded=False):
            st.markdown(
                """
Pathfind uses a compact swipe flow: the app draws a small set of swipe cards per run.
- The selection is randomized but stable within a run.
- Each swipe updates weights and preferences (e.g., climate preference, cost emphasis, air quality).
                """
            )

        with st.expander("Step 4 — Optional Extensions (e.g., Tarot inspiration)", expanded=False):
            st.markdown(
                """
Users can optionally activate playful extensions that modify the candidate set or apply controlled boosts.
                """
            )

        with st.expander("Step 5 — Ban List / Region Exclusions (Optional)", expanded=False):
            st.markdown(
                """
Users can exclude world regions.  
Excluded regions are mapped to ISO3 country lists and removed prior to scoring.
                """
            )

        with st.expander("Step 6 — Matching Results + Explanation", expanded=False):
            st.markdown(
                """
The system loads the base dataset, applies filters, computes sub-scores and a final score, and displays top destinations.
Each result includes an explanation showing how categories contributed to the match.
                """
            )

        with st.expander("Step 7 — Country Dashboard + Planning", expanded=False):
            st.markdown(
                """
Users inspect destination details and can use planning modules:
- Cost Estimator (trip budgeting)
- Trip Planner (itinerary / routing support)
- Optional chat assistance for questions and planning (if enabled)
                """
            )

        with st.expander("Step 8–9 — Booking + Confirmation (Flights + Calendar Export)", expanded=False):
            st.markdown(
                """
Users can proceed to flight search and optionally export calendar events via Google OAuth (if enabled).
                """
            )

        st.markdown("---")
        _mini_card(
            "Run behavior (freshness)",
            _html_list(
                [
                    "Within a run, randomized components remain stable so the experience is consistent.",
                    "Starting a new run resets the flow and refreshes randomized elements for variety.",
                ]
            ),
        )

    # ------------------------------------------------------------
    # DATA & SOURCES
    # ------------------------------------------------------------
    with tabs[2]:
        _section_title("Data & Sources", "Database structure, providers, and credits")

        st.markdown(
            """
All structured country-level data is stored in a unified SQLite database (`unified_country_database.db`), which serves as the single source of truth.
The database combines curated data and regularly updated snapshots of external sources.
            """
        )

        st.markdown(
            """
### How the database is organized (conceptual)

Pathfind is built around a **country backbone** that uses standardized **ISO3 country codes** to merge data from multiple domains.
Instead of keeping everything in one wide file, the project stores **domain-specific entities** in separate tables and joins them when assembling the dashboard views.

In practice, the database contains:
- a **country reference layer** (country names, ISO codes, metadata),
- **indices and prices** (cost-of-living indices, item definitions, item prices, exchange-rate snapshots),
- **travel information** (entry requirements, safety notes, health guidance, local laws, offices),
- **context signals** (heritage sites, climate aggregates),
- **travel/transport connectors** (airport mappings and flight-cost samples).

When Pathfind builds the candidate set for scoring, it merges these entities primarily through **ISO3 keys** (and, for flights, via **airport/IATA mappings**).
This structure keeps the system maintainable (tables can be updated independently) and makes it easier to explain where each signal originates.
            """
        )

        _mini_card(
            "Examples of entities (not exhaustive)",
            _html_list(
                [
                    "<b>countries</b>: ISO3 backbone and country metadata",
                    "<b>numbeo_indices / numbeo_items / numbeo_prices</b>: indices, item taxonomy, and price snapshots used for both scoring and budgeting",
                    "<b>tugo_entry / tugo_safety / tugo_health / tugo_laws / tugo_offices</b>: structured travel information stored as database tables",
                    "<b>unesco_by_country / unesco_heritage_sites</b>: heritage counts and site metadata",
                    "<b>climate_monthly</b>: aggregated climate indicators (monthly averages)",
                    "<b>airports / flight_costs</b>: airport mapping layer and flight-cost samples for fast flight context",
                ]
            ),
        )

        st.markdown("### How the base dataset is assembled")
        st.markdown(
            """
Pathfind assembles a country-level candidate dataset by joining:
- a core country table with indices/prices, climate aggregates, heritage counts, and equality-related indicators,
- and (optionally) flight context via airport mapping + flight cost samples.  

After joins, the dataset is deduplicated to one row per country (ISO3), preferring rows with fewer missing values.  
This provides a stable base for ranking while keeping the underlying entities modular and updateable.
            """
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        _mini_card(
            "Data providers & credits",
            _html_list(
                [
                    "<b>Numbeo</b> — cost of living indices and item-level prices (scoring + cost estimator)",
                    "<b>Tugo</b> — travel advisories (safety / health / entry), stored as database tables",
                    "<b>Auswärtiges Amt</b> — official travel information (Germany)",
                    "<b>UNESCO</b> — World Heritage Sites (counts and site metadata)",
                    "<b>Berkeley Earth</b> — climate and weather data inputs",
                    "<b>Amadeus</b> — live flight search and itinerary/price signals<br>&nbsp;&nbsp;• Flight Offers Search API<br>&nbsp;&nbsp;• Flight Offers Price API<br>&nbsp;&nbsp;• Flight Create Orders API",
                    "<b>Google APIs</b> — calendar export (OAuth) + maps/routing support<br>&nbsp;&nbsp;• Google Calendar API<br>&nbsp;&nbsp;• Google Places API<br>&nbsp;&nbsp;• Google Routes API",
                    "<b>Serper API</b> — performs web search to search prices for trip planner",
                    "<b>OpenAI</b> — chatbot interaction and generated explanations",
                    "<b>Roxy</b> — tarot card draw (optional extension)",
                    "<b>Travel Buddy</b> — visa requirements matched to the user’s nationality",
                    "<b>OpenTravelData (Github)</b> — data for airports",
                    "<b>gettocenter.com</b> — scraped to obtain passenger volume of airports",
                    "<b>Unsplash API</b> — images for countries",
                ]
            ),
        )

        _mini_card(
            "API keys and setup note",
            _html_list(
                [
                    "Some functionality requires API keys (e.g., flights, routing, chatbot interaction).",
                    "In addition, some database-backed signals originate from providers whose data is refreshed over time (e.g., travel advisories).",
                    "Setup instructions, dependencies, and packages are documented in the GitHub repository.",
                ]
            ),
        )

        _mini_card(
            "Important note",
            "Several signals are country-level aggregates. They provide guidance but cannot capture city-level or individual-level variation.",
        )

    # ------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------
    with tabs[3]:
        _section_title("Scoring", "Explainable matching and ranking")

        st.markdown(
            """
Pathfind computes interpretable sub-scores in the range 0–1 and combines them into a final score using user-defined weights.
The goal is transparency: users should be able to understand why a destination ranks high or low.

At a high level, scoring follows the same structure across categories:

1) build a clean country-level dataset (joined by ISO3)  
2) transform raw indicators into comparable 0–1 sub-scores  
3) combine sub-scores using weights derived from personas + interactions  
4) produce explanations that show category contributions (“Peek behind the score”)
            """
        )

        with st.expander("Step A — Candidate set & preprocessing", expanded=True):
            st.markdown(
                """
Before any scoring happens, Pathfind constructs a candidate set of countries:

- Countries are loaded from the unified database and merged across domains using ISO3 keys.
- Filters remove countries that should not be considered (e.g., region exclusions or safety-related filters).
- If multiple rows can exist for a country after joins (due to missingness or duplicates), the dataset is deduplicated to a single ISO3 row.
                """
            )

        with st.expander("Step B — Missing value handling (neutral & conservative)", expanded=False):
            st.markdown(
                """
Pathfind integrates multiple data sources (e.g., cost indices, climate, flights, safety and equality indicators).
Because coverage differs across providers, some values can be missing.

Missing values are handled conservatively to keep the ranking stable and fair:

- If multiple records exist for a country, the version with the fewest missing values is retained.
- For most numeric indices, missing values are replaced with the median across available countries, resulting in a neutral “middle-of-the-pack” contribution.
- If an entire feature is unavailable, it is treated as neutral so it does not distort the ranking.
- Feature-specific rules apply where necessary (e.g., missing equality data cannot pass the LGBTQ+ filter).
- In the UI (e.g., cost estimator or flight information), missing data is explicitly marked rather than guessed.

This strategy avoids automatically penalizing destinations simply because some data is unavailable.
                """
            )
        
        with st.expander("Step C — Outlier handling (winsorization)", expanded=False):
            st.markdown(
                """
Raw indicators can contain extreme values that would dominate a min–max scaling.
To keep the ranking stable, Pathfind applies winsorization to numeric indicators:

- Values below the 5th percentile are capped at the 5th percentile.
- Values above the 95th percentile are capped at the 95th percentile.

This keeps scoring sensitive to meaningful differences while preventing single outliers from pushing everything else toward 0.
                """
            )

        with st.expander("Step D — Normalization to 0–1", expanded=False):
            st.markdown(
                """
After winsorization, indicators are normalized to a common scale:

- Standard approach: min–max scaling to the range 0–1.
- Direction is aligned to “higher is better” for each category.

Examples:
- lower cost-of-living → higher cost score (inverted scale)
- lower pollution → higher clean-air score (inverted scale)
- closer to preferred temperature → higher weather score (distance-to-target transformed to 0–1)
- higher purchasing power or QoL → higher score (direct scale)

The result is a set of comparable sub-scores per country, each interpretable on a 0–1 scale.
                """
            )

        with st.expander("Step E — Weighting and aggregation", expanded=False):
            st.markdown(
                """
Weights represent “importance budgets” over categories:

- Persona selection provides a sensible default weight profile.
- Swipe interactions refine weights and can also update user targets (e.g., preferred climate range).
- Weights are represented as 0–100 values and normalized so they always sum to 100.

**Swipe decisions are modeled as explicit trade-offs.**  
Increasing the importance of one dimension intentionally reduces the influence of others.
This ensures that preferences meaningfully reshape the ranking instead of uniformly increasing all scores.

Final aggregation:
- `final_score_raw` is computed as a weighted sum of sub-scores.
- The final score is kept comparable (not artificially rescaled to force #1 to 100%).
- Countries are ranked by this score and displayed as Top Matches.
                """
            )

        with st.expander("Step F — Explanations (“Peek behind the score”)", expanded=False):
            st.markdown(
                """
Pathfind creates user-facing explanations by keeping intermediate quantities explicit:

- Sub-scores remain accessible (e.g., cost score, clean-air score, climate score, safety-related scores).
- Each sub-score is multiplied by its current weight to form a contribution.
- Explanations summarize the top positive and negative contributions so users can see what drives ranking.

This is intentionally not a black-box model: the scoring pipeline is designed to be inspectable and debuggable.
                """
            )

        with st.expander("Controlled randomness (stability within a run)", expanded=False):
            st.markdown(
                """
Pathfind uses controlled randomness to diversify close outcomes and break ties.

- Randomized elements remain stable within a run so behavior is reproducible when debugging.
- A new run refreshes randomized components for variety.

This avoids the situation where tiny floating-point differences or ties make rankings feel repetitive, while still keeping the system understandable.
                """
            )

    # ------------------------------------------------------------
    # MODULES (merged)
    # ------------------------------------------------------------
    with tabs[4]:
        _section_title("Modules", "Core components in the dashboard")

        st.markdown(
            """
Pathfind is implemented as a modular set of mini-apps inside one unified dashboard.
The core ranking is database-driven (fast and repeatable), while several modules add live functionality through APIs.
            """
        )

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "Cost Estimator (budget planning)",
                _html_list(
                    [
                        "Uses item-level prices and indices to translate “cost of living” into a planning budget.",
                        "Builds a transparent breakdown (e.g., food, transport, everyday items) rather than one opaque number.",
                        "Scales by trip duration and group size; can incorporate exchange-rate snapshots when available.",
                        "Designed for planning and comparison — real costs vary by location, season, and travel style.",
                    ]
                ),
            )
        with b:
            _mini_card(
                "Flight Search (DB; live)",
                _html_list(
                    [
                        "Destinations Page: estimated flight costs from the database <br>&nbsp;&nbsp;• Note: because of rate limits estimated flight costs are only available when Germany or US are selected as nationality)",
                        "Flight Search Module: live flight search via Amadeus when the user proceeds (dates, passengers, origin/destination airports).<br>&nbsp;&nbsp;• Provides the complete experience: <div style='margin-top:8px; display:flex; align-items:center; gap:6px; font-size:0.85rem;'><span style='background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);'>Search Flight</span><span style='opacity:0.4;'>→</span><span style='background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);'>Book Flight</span><span style='opacity:0.4;'>→</span><span style='background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.1);'>Add flight to Calendar</span></div>"
                        ""
                    ]
                ),
            )

        a, b = st.columns([1, 1])
        with a:
            _mini_card(
                "Trip Planner",
                (
                    "<div style='font-size:0.88rem; border-left: 3px solid #1f6e8a; padding-left: 12px; margin-bottom: 12px;'>"
                    "<b>1. Initialization (Parallel)</b><br>"
                    "• <i>Chatbot:</i> Analyzes user prompt to extract intent and constraints.<br>"
                    "• <i>SQLite:</i> Concurrently retrieves exchange rates and ISO metadata to calibrate the budget engine."
                    "</div>"
                    "<div style='font-size:0.88rem; border-left: 3px solid #1f6e8a; padding-left: 12px; margin-bottom: 12px;'>"
                    "<b>2. Discovery (Chatbot → Places API)</b><br>"
                    "• <i>Chatbot:</i> Formulates specific search queries based on user interests.<br>"
                    "• <i>Google Places API:</i> Executes these searches in parallel to find real-world venues."
                    "</div>"
                    "<div style='font-size:0.88rem; border-left: 3px solid #1f6e8a; padding-left: 12px; margin-bottom: 12px;'>"
                    "<b>3. Enrichment (Places → Serper API)</b><br>"
                    "• <i>System:</i> Feeds discovered venue names into Serper for cost verification.<br>"
                    "• <i>Serper API:</i> Scrapes real-time entrance fees and menu costs for the chatbot's candidates in parallel."
                    "</div>"
                    "<div style='font-size:0.88rem; border-left: 3px solid #1f6e8a; padding-left: 12px; margin-bottom: 12px;'>"
                    "<b>4. Synthesis (Data → Chatbot → Logic)</b><br>"
                    "• <i>Chatbot:</i> Synthesizes the final itinerary text using the enriched data.<br>"
                    "• <i>Logic Engine:</i> Python logic calculates final costs using traveler multipliers and exchange rates and Google Routes optimization to the chatbot's plan."
                    "</div>"
                    "<div style='font-size:0.88rem; border-left: 3px solid #1f6e8a; padding-left: 12px;'>"
                    "<b>5. Visualization & Export</b><br>"
                    "• <i>Folium:</i> Maps the final itinerary with interactive markers and polylines.<br>"
                    "• <i>WeasyPrint:</i> Converts the chatbot's conversational output into a structured PDF."
                    "</div>"
                )
            )
        with b:
            _mini_card(
                "Chatbot interaction (Q&A and planning support)",
                _html_list(
                    [
                        "Natural-language interface for questions about destinations, safety context, budgets, and planning.",
                        "Can generate itinerary ideas under constraints (e.g., “2 days, low budget, nature + cafés”).",
                        "Can explain rankings (“why is X high?”) by referencing sub-scores and weights.",
                        "Human-in-the-loop: the user controls preferences; the assistant supports exploration and explanation.",
                    ]
                ),
            )

        st.markdown(
            """
Export and reporting features (e.g., PDF summaries) can be enabled in the main dashboard to support planning and sharing.
            """
        )

    # ------------------------------------------------------------
    # WHAT MAKES PATHFIND SPECIAL 
    # ------------------------------------------------------------
    with tabs[5]:
        _section_title("What makes Pathfind special", "Design choices, performance, and future potential")

        row1a, row1b = st.columns([1, 1])
        with row1a:
            _mini_card(
                "Modular mini-app architecture",
                _html_list(
                    [
                        "Features are implemented as separate modules and orchestrated in the main dashboard",
                        "Improves maintainability, testability, and parallel team development",
                        "Enables isolated debugging of individual components",
                    ]
                ),
            )
        with row1b:
            _mini_card(
                "Performance-aware design",
                _html_list(
                    [
                        "Unified SQLite database as single source of truth for most signals",
                        "Two-stage design: DB-backed estimates first, optional live APIs second",
                        "Avoids unnecessary API calls and keeps the dashboard responsive",
                        "Leverages parallel execution for concurrent API calls and database lookups, significantly reducing latency during complex planning workflows which brought down the result generation of the trip planner from around 6 minutes to around 2 minutes",
                    ]
                ),
            )

        row2a, row2b = st.columns([1, 1])
        with row2a:
            _mini_card(
                "Debug-friendly & reproducible",
                _html_list(
                    [
                        "Intermediate sub-scores make behavior transparent",
                        "Within-run stability supports reproducibility during debugging",
                        "Issues can be reproduced systematically when a configuration is known",
                    ]
                ),
            )
        with row2b:
            _mini_card(
                "Hybrid live system",
                _html_list(
                    [
                        "Live modules rely on API calls (flights, routing, chat interaction)",
                        "Database stores curated data and regularly updated snapshots (e.g., advisories)",
                        "Clear separation between fast offline-capable signals and live services",
                    ]
                ),
            )

        row3a, row3b = st.columns([1, 1])
        with row3a:
            _mini_card(
                "Explainability first",
                _html_list(
                    [
                        "No black-box recommendation model",
                        "Users can inspect why a destination ranks high or low",
                        "Score explanations connect preferences to outcomes",
                    ]
                ),
            )
        with row3b:
            _mini_card(
                "Beyond typical travel planners",
                _html_list(
                    [
                        "Not centered solely around booking conversion",
                        "Integrates contextual indicators (entry, safety, equality, heritage, climate, affordability)",
                        "Designed for exploration, transparency, and research-oriented comparison",
                    ]
                ),
            )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        
        _mini_card(
            "Future Potential",
            (
                "<div style='margin-bottom:10px;'>"
                "Due to limited time and student resources, we focused on implementing the core features end-to-end and optimizing them for stability, performance, and explainability. "
                "If we had more time and resources, we would expand Pathfind in the following areas:"
                "</div>"

                "<div style='font-weight:700; margin-top:10px; margin-bottom:6px;'>Granularity (country → city)</div>"
                "<ul style='margin-top:0; line-height:1.9;'>"
                "<li>City-level views in addition to country-level aggregates for more precise recommendations.</li>"
                "<li>Better within-country differentiation (regional climates, costs, safety context).</li>"
                "</ul>"

                "<div style='font-weight:700; margin-top:10px; margin-bottom:6px;'>User accounts &amp; persistence</div>"
                "<ul style='margin-top:0; line-height:1.9;'>"
                "<li>User profiles with saved favorites, stored preferences, and trip plans across sessions.</li>"
                "<li>Personal planning workspace (itineraries, notes, exports) tied to an account.</li>"
                "</ul>"

                "<div style='font-weight:700; margin-top:10px; margin-bottom:6px;'>Personas &amp; customization</div>"
                "<ul style='margin-top:0; line-height:1.9;'>"
                "<li>More variation in the persona library (additional archetypes + fine-grained subtypes).</li>"
                "<li>Fully custom personas (saveable) created from user-defined weight templates.</li>"
                "</ul>"

                "<div style='font-weight:700; margin-top:10px; margin-bottom:6px;'>Chatbot expansion</div>"
                "<ul style='margin-top:0; line-height:1.9;'>"
                "<li>Generate personas from a short user chat (preferences → persona profile).</li>"
                "<li>A chatbot that can chat over the full internal dataset (currently constrained by API cost limits).</li>"
                "<li>More in-flow chat usage for planning (itinerary drafts, constraints, follow-up questions).</li>"
                "</ul>"
            ),
        )

    # ------------------------------------------------------------
    # IMPRESSUM (now includes privacy notice + github link)
    # ------------------------------------------------------------
    with tabs[6]:
        _section_title("Impressum", "Project context, contributors, and privacy notice")

        st.markdown(
            """
This dashboard was developed as part of a university group project.

**Professor:** Marc Ratkovic  
**Chair:** Chair of Social Data Science  
**Module:** Seminar and Lab Machine Learning  
            """
        )

        _mini_card(
            "Producers",
            _html_list(
                [
                    "Fritz Bumb",
                    "Clara Oppenländer",
                    "Luis Nepomuk Götze",
                    "Thomas Petrausch",
                ]
            ),
        )

        _mini_card(
            "Repository",
            "GitHub: https://github.com/clara-opp/pathfind",
        )

        _mini_card(
            "Privacy notice / data protection",
            _html_list(
                [
                    "Pathfind does not permanently store personal user data.",
                    "User inputs and preferences are handled within the Streamlit session context.",
                    "API keys are never shown in the UI and should be provided via environment variables during development/deployment.",
                    "This dashboard is intended for research, learning, and demonstration purposes.",
                ]
            ),
        )

        today = datetime.date.today().strftime("%Y-%m-%d")
        st.caption(f"Last rendered: {today}")


# Optional: allow quick standalone testing
# streamlit run modules/about_page.py
if __name__ == "__main__":
    render_about_page()

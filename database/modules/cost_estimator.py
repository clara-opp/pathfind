# modules/cost_estimator.py
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional

# ============================================================
# Public API (this is what travel_planner imports)
# ============================================================

def render_cost_estimator(
    iso3: str,
    days_default: int = 7,
    adults_default: int = 2,
    kids_default: int = 0,
    db_path: Optional[str] = None,
    key_prefix: str = "ce",
):
    """
    Render the Trip Cost Estimator UI inside any Streamlit container/tab.

    Parameters
    ----------
    iso3 : str
        ISO3 country code for looking up Numbeo prices in the DB.
    days_default : int
        Default trip length (days), e.g. derived from app's start/end dates.
    adults_default : int
        Default adults.
    kids_default : int
        Default kids.
    db_path : str | None
        Optional explicit SQLite db path. If None, auto-resolves.
    key_prefix : str
        Namespace for Streamlit session_state keys to avoid collisions.
    """

    # ---------------------------
    # Config / Constants
    # ---------------------------
    CATEGORY_ORDER = ["Food & Drinks", "Accommodation", "Local Transport", "Entertainment", "Shopping & Souvenirs"]

    DIAL_LABELS = ["Minimal", "Budget", "Typical", "Comfortable", "Premium"]
    LABEL_TO_DIAL = {
        "Minimal": 0.15,
        "Budget": 0.60,
        "Typical": 1.00,
        "Comfortable": 1.60,
        "Premium": 2.50,
    }

    TRAVEL_STYLES = ["Low Budget", "Balanced", "Comfortable", "Customised"]
    STYLE_DEFAULT_LABELS = {
        "Low Budget": {
            "Food & Drinks": "Budget",
            "Accommodation": "Budget",
            "Local Transport": "Budget",
            "Entertainment": "Minimal",
            "Shopping & Souvenirs": "Minimal",
        },
        "Balanced": {
            "Food & Drinks": "Typical",
            "Accommodation": "Typical",
            "Local Transport": "Typical",
            "Entertainment": "Typical",
            "Shopping & Souvenirs": "Typical",
        },
        "Comfortable": {
            "Food & Drinks": "Comfortable",
            "Accommodation": "Comfortable",
            "Local Transport": "Comfortable",
            "Entertainment": "Comfortable",
            "Shopping & Souvenirs": "Comfortable",
        },
    }

    COST_SCENARIOS = ["Optimistic", "Average", "Conservative"]
    SCENARIO_TO_PRICE_COL = {
        "Optimistic": "lowest_price",
        "Average": "average_price",
        "Conservative": "highest_price",
    }

    CATEGORY_EXPLANATIONS = {
        "Food & Drinks": (
            "Estimates daily spending on food and beverages, anchored on inexpensive local restaurant meals plus everyday drinks. "
            "Restaurant prices can also serve as a proxy for grocery based cooking, since food costs tend to move together across countries."
        ),
        "Accommodation": (
            "Approximates housing costs using average city centre apartment rents scaled to your trip length. "
            "Apartment size is selected automatically by group size to reflect realistic space needs; this may slightly overestimate costs, "
            "but helps avoid unrealistically low housing estimates."
        ),
        "Local Transport": (
            "Captures local mobility costs such as public transport and taxis, reflecting typical travel within the city during your stay."
        ),
        "Entertainment": (
            "Represents leisure spending using common price anchors such as cinema, fitness, and sports services as a proxy for overall leisure costs."
        ),
        "Shopping & Souvenirs": (
            "Estimates incidental and discretionary spending using stable international price anchors such as common clothing items."
        ),
    }

    # ---- Updated base levels (your latest choices) ----
    DEFAULT_ITEMS = {
        "Food & Drinks": [
            ("Meal at an Inexpensive Restaurant", "per_person_per_day", 1.00),
            ("Cappuccino", "per_person_per_day", 0.70),
            ("Soft Drink (Coca-Cola or Pepsi", "per_person_per_day", 0.40),
            ("Bottled Water (0.33 Liter)", "per_person_per_day", 1.00),
            ("Domestic Draft Beer (0.5 Liter)", "per_person_per_day", 0.30),
            ("Imported Beer (0.33 Liter Bottle)", "per_person_per_day", 0.20),
        ],
        "Local Transport": [
            ("One-Way Ticket (Local Transport)", "per_person_per_day", 1.50),
            ("Taxi Start (Standard Tariff)", "per_trip", 1.50),
            ("Taxi 1 km (Standard Tariff)", "per_km", 10.00),
            ("Monthly Public Transport Pass", "per_person_per_month", 0.00),
        ],
        "Entertainment": [
            ("Cinema Ticket (International Release)", "per_person_per_week", 2.00),
            ("Monthly Fitness Club Membership", "per_person_per_month", 0.30),
            ("Tennis Court Rental (1 Hour, Weekend)", "per_person_per_week", 0.50),
        ],
        "Shopping & Souvenirs": [
            ("Jeans (Levi's 501", "per_item", 0.50),
            ("Summer Dress in a Chain Store", "per_item", 0.50),
            ("Nike Running Shoes", "per_item", 0.50),
        ],
        "Accommodation": [
            ("1 Bedroom Apartment in City Centre", "per_month_household", 1.0),
            ("3 Bedroom Apartment in City Centre", "per_month_household", 0.0),
        ],
    }

    # ---------------------------
    # Key helpers
    # ---------------------------
    def k(name: str) -> str:
        return f"{key_prefix}_{name}"

    # ============================================================
    # DB helpers
    # ============================================================
    DEFAULT_DB = "unified_country_database.db"

    def resolve_db_path(db_name: str = DEFAULT_DB) -> str:
        here = Path(__file__).parent.parent  # modules/.. = app folder
        candidates = [
            here / db_name,
            here / "data" / db_name,
            Path.cwd() / db_name,
            Path.cwd() / "data" / db_name,
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return str(here / db_name)

    @st.cache_data(show_spinner=False)
    def load_exchange_rates(_db_path: str) -> pd.DataFrame:
        with sqlite3.connect(_db_path) as conn:
            return pd.read_sql(
                "SELECT currency, one_eur_to_currency, one_usd_to_currency FROM numbeo_exchange_rates",
                conn,
            )

    @st.cache_data(show_spinner=False)
    def load_country_prices(_db_path: str, _iso3: str) -> pd.DataFrame:
        with sqlite3.connect(_db_path) as conn:
            df = pd.read_sql(
                """
                SELECT
                  item_id,
                  item_name,
                  lowest_price,
                  average_price,
                  highest_price,
                  country_name,
                  currency,
                  iso3
                FROM numbeo_prices
                WHERE iso3 = ?
                """,
                conn,
                params=(_iso3,),
            )
        for c in ["lowest_price", "average_price", "highest_price"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["item_name"] = df["item_name"].astype(str)
        return df

    # ============================================================
    # Small utils
    # ============================================================
    def split_item_category(item_name: str) -> Tuple[str, str]:
        if not isinstance(item_name, str):
            return ("Other", str(item_name))
        parts = [p.strip() for p in item_name.split(",")]
        if len(parts) >= 2:
            category = parts[-1]
            name = ", ".join(parts[:-1]).strip()
            return (category, name)
        return ("Other", item_name.strip())

    def clamp_nonneg(x: float) -> float:
        try:
            x = float(x)
        except Exception:
            return 0.0
        return max(0.0, x)

    def days_to_month_factor(days: int) -> float:
        return float(days) / 30.0

    def money(x: float, prefix: str) -> str:
        try:
            # german formatting (comma decimal)
            return f"{prefix}{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return f"{prefix}{x}"

    def find_price_row(prices_df: pd.DataFrame, pattern: str) -> Optional[pd.Series]:
        if prices_df.empty or not pattern:
            return None
        mask = prices_df["item_name"].str.contains(str(pattern), case=False, na=False, regex=False)
        hits = prices_df[mask].copy()
        if hits.empty:
            return None
        hits["avg_ok"] = hits["average_price"].notna().astype(int)
        hits = hits.sort_values(["avg_ok"], ascending=False)
        return hits.iloc[0]

    def compute_unit_multiplier(unit_type: str, days: int, adults: int, kids: int) -> float:
        persons = max(adults + kids, 1)
        if unit_type == "per_person_per_day":
            return float(persons) * float(days)
        if unit_type == "per_person_per_week":
            return float(persons) * (float(days) / 7.0)
        if unit_type == "per_person_per_month":
            return float(persons) * days_to_month_factor(days)
        if unit_type == "per_month_household":
            return 1.0 * days_to_month_factor(days)
        return 1.0  # per_trip / per_item / per_km

    def build_default_plan(prices_df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for cat, items in DEFAULT_ITEMS.items():
            for pattern, unit_type, base_qty in items:
                row = find_price_row(prices_df, pattern)
                if row is None:
                    rows.append(
                        {
                            "category": cat,
                            "pattern": pattern,
                            "unit_type": unit_type,
                            "base_qty": float(base_qty),
                            "item_id": None,
                            "item_name_full": None,
                            "item_name_short": pattern,
                            "currency": None,
                        }
                    )
                else:
                    _, name_short = split_item_category(row["item_name"])
                    rows.append(
                        {
                            "category": cat,
                            "pattern": pattern,
                            "unit_type": unit_type,
                            "base_qty": float(base_qty),
                            "item_id": row.get("item_id", None),
                            "item_name_full": row["item_name"],
                            "item_name_short": name_short,
                            "currency": row.get("currency", None),
                        }
                    )
        return pd.DataFrame(rows)

    def get_rate_eur_to_currency(exchange_df: pd.DataFrame, currency: str) -> Optional[float]:
        if exchange_df.empty or not currency:
            return None
        row = exchange_df[exchange_df["currency"] == currency]
        if row.empty:
            return None
        r = row.iloc[0].get("one_eur_to_currency", None)
        if r is None or pd.isna(r) or float(r) == 0:
            return None
        return float(r)

    def compute_costs(
        prices_df: pd.DataFrame,
        plan_df: pd.DataFrame,
        exchange_df: pd.DataFrame,
        price_col: str,
        days: int,
        adults: int,
        kids: int,
        category_dials: Dict[str, float],
    ) -> Tuple[pd.DataFrame, Dict[str, float], Dict[str, float], str]:
        if plan_df is None or plan_df.empty:
            return pd.DataFrame(), {}, {}, ""

        local_currency = ""
        if "currency" in prices_df.columns and prices_df["currency"].notna().any():
            local_currency = str(prices_df["currency"].dropna().iloc[0])

        price_map = {str(r["item_name"]): r for _, r in prices_df.iterrows()}

        out_rows = []
        for _, r in plan_df.iterrows():
            cat = r["category"]
            dial = float(category_dials.get(cat, 1.0))

            full_name = r.get("item_name_full", None)
            if full_name and full_name in price_map:
                pr = price_map[full_name]
                price_val = pr.get(price_col, None)
            else:
                pr_series = find_price_row(prices_df, str(r.get("pattern", "")))
                price_val = pr_series.get(price_col, None) if pr_series is not None else None

            unit_type = str(r.get("unit_type", "per_trip"))
            base_qty = clamp_nonneg(r.get("base_qty", 0.0))

            # Core logic:
            # final amount = reference amount * spending multiplier * trip scaling
            spending_multiplier = dial
            reference_amount = base_qty
            final_amount = reference_amount * spending_multiplier

            unit_mult = compute_unit_multiplier(unit_type, days, adults, kids)
            effective_units = final_amount * unit_mult

            total_local = None
            if price_val is not None and not pd.isna(price_val):
                total_local = float(price_val) * float(effective_units)

            rate = get_rate_eur_to_currency(exchange_df, local_currency)
            total_eur = None
            if total_local is not None and rate is not None:
                total_eur = float(total_local) / float(rate)

            out_rows.append(
                {
                    "category": cat,
                    "item": r.get("item_name_short", r.get("pattern", "")),
                    "reference_amount": reference_amount,
                    "spending_multiplier": spending_multiplier,
                    "final_amount": final_amount,
                    "trip_quantity": float(effective_units),
                    "unit_type": unit_type,
                    "unit_price_local": None if price_val is None or pd.isna(price_val) else float(price_val),
                    "total_local": total_local,
                    "total_eur": total_eur,
                    "missing_price": (price_val is None or pd.isna(price_val)),
                }
            )

        detailed = pd.DataFrame(out_rows)

        cat_local = (
            detailed.dropna(subset=["total_local"])
            .groupby("category")["total_local"]
            .sum()
            .to_dict()
        )
        cat_eur = (
            detailed.dropna(subset=["total_eur"])
            .groupby("category")["total_eur"]
            .sum()
            .to_dict()
        )

        return detailed, cat_local, cat_eur, local_currency

    def category_has_any_price_data(detailed: pd.DataFrame, cat: str) -> bool:
        sub = detailed[detailed["category"] == cat]
        if sub.empty:
            return False
        return sub["total_local"].notna().any() or sub["total_eur"].notna().any()

    # ============================================================
    # State init
    # ============================================================
    _db_path = db_path or resolve_db_path(DEFAULT_DB)

    if k("init") not in st.session_state:
        st.session_state[k("init")] = True

        st.session_state[k("days")] = int(max(1, days_default))
        st.session_state[k("adults")] = int(max(1, adults_default))
        st.session_state[k("kids")] = int(max(0, kids_default))

        st.session_state[k("travel_style")] = "Balanced"
        st.session_state[k("_applying_style")] = False
        st.session_state[k("advanced_mode")] = False

        st.session_state[k("cost_scenario")] = "Average"

        st.session_state[k("category_dials")] = {c: 1.0 for c in CATEGORY_ORDER}
        for cat in CATEGORY_ORDER:
            st.session_state[k(f"dial_label_{cat}")] = "Typical"

        st.session_state[k("plan_df")] = None

        # ---- NEW: days lock state ----
        st.session_state[k("unlock_days")] = False
        st.session_state[k("last_iso3")] = str(iso3)
        st.session_state[k("last_days_default")] = int(max(1, days_default))

    # ============================================================
    # Force re-lock when switching countries or trip duration changes
    # (must happen BEFORE creating the Days slider)
    # ============================================================
    incoming_iso3 = str(iso3)
    incoming_days_default = int(max(1, days_default))

    iso_changed = st.session_state.get(k("last_iso3")) != incoming_iso3
    triplen_changed = st.session_state.get(k("last_days_default")) != incoming_days_default

    if iso_changed or triplen_changed:
        st.session_state[k("last_iso3")] = incoming_iso3
        st.session_state[k("last_days_default")] = incoming_days_default
        st.session_state[k("unlock_days")] = False
        st.session_state[k("days")] = incoming_days_default

    # ============================================================
    # Style / behaviour
    # ============================================================
    def mark_customised():
        if st.session_state.get(k("_applying_style"), False):
            return
        if st.session_state.get(k("travel_style")) != "Customised":
            st.session_state[k("travel_style")] = "Customised"
            # IMPORTANT: also update the selectbox widget key (style_select)
            st.session_state[k("style_select")] = "Customised"

    def apply_style(style: str, prices_df_for_reset: pd.DataFrame):
        if style not in STYLE_DEFAULT_LABELS:
            return

        st.session_state[k("_applying_style")] = True

        # 1) set style state
        st.session_state[k("travel_style")] = style
        st.session_state[k("style_select")] = style

        # 2) reset plan reference amounts to defaults (so presets truly revert everything)
        st.session_state[k("plan_df")] = build_default_plan(prices_df_for_reset)

        # 3) set dial labels + dial multipliers
        labels = STYLE_DEFAULT_LABELS[style]
        for cat in CATEGORY_ORDER:
            lab = labels.get(cat, "Typical")
            st.session_state[k(f"dial_label_{cat}")] = lab
            st.session_state[k("category_dials")][cat] = LABEL_TO_DIAL.get(lab, 1.0)

        st.session_state[k("_applying_style")] = False

    def on_style_change(prices_df_for_reset: pd.DataFrame):
        style = st.session_state.get(k("style_select"), "Balanced")
        if style in STYLE_DEFAULT_LABELS:
            apply_style(style, prices_df_for_reset)
        else:
            st.session_state[k("travel_style")] = "Customised"

    def on_dial_change(cat: str):
        label = st.session_state.get(k(f"dial_label_{cat}"), "Typical")
        st.session_state[k("category_dials")][cat] = LABEL_TO_DIAL.get(label, 1.0)
        mark_customised()

    # Accommodation proxy by people (auto 1BR vs 3BR) BUT still user can override via Advanced.
    # We'll apply this only when plan exists and ONLY if user has not manually modified accommodation rows yet.
    def set_accommodation_proxy_by_people(adults: int, kids: int):
        persons = int(adults) + int(kids)
        use_3br = persons >= 3

        plan = st.session_state.get(k("plan_df"))
        if plan is None or getattr(plan, "empty", True):
            return

        acc = plan[plan["category"] == "Accommodation"].copy()
        if acc.empty:
            return

        idx_1br = None
        idx_3br = None
        for idx, r in acc.iterrows():
            pat = str(r["pattern"])
            if "1 Bedroom Apartment in City Centre" in pat:
                idx_1br = idx
            elif "3 Bedroom Apartment in City Centre" in pat:
                idx_3br = idx

        # if both are manually set to something already, do not override here
        # heuristic: if sum(base_qty) not in {0,1} -> user customised accommodation
        s = float(acc["base_qty"].sum())
        if s not in (0.0, 1.0):
            return

        # auto pick (allow 0 overall if user sets both 0 in advanced; but auto default should choose one)
        if idx_1br is not None:
            plan.loc[idx_1br, "base_qty"] = 0.0
        if idx_3br is not None:
            plan.loc[idx_3br, "base_qty"] = 0.0

        if use_3br and idx_3br is not None:
            plan.loc[idx_3br, "base_qty"] = 1.0
        elif idx_1br is not None:
            plan.loc[idx_1br, "base_qty"] = 1.0

        st.session_state[k("plan_df")] = plan

    # ============================================================
    # Load data
    # ============================================================
    prices_df = load_country_prices(_db_path, iso3)
    exchange_df = load_exchange_rates(_db_path)

    if prices_df.empty:
        st.warning("No Numbeo price rows found for this country (ISO3).")
        return

    # Build plan on first time
    if st.session_state.get(k("plan_df")) is None:
        st.session_state[k("plan_df")] = build_default_plan(prices_df)
        # apply current preset (Balanced default)
        apply_style(st.session_state.get(k("travel_style"), "Balanced"), prices_df)

    # ============================================================
    # UI
    # ============================================================
    st.markdown("### 💰 Trip Cost Estimator")

    # Trip setup
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        # lock UI: checkbox like "Show details"
        st.checkbox(
            "Unlock Days",
            value=bool(st.session_state.get(k("unlock_days"), False)),
            key=k("unlock_days"),
        )

        # If locked, always force slider value to trip length BEFORE widget creation
        if not st.session_state.get(k("unlock_days"), False):
            st.session_state[k("days")] = incoming_days_default

        st.caption("Tip: *Days* follows your trip dates by default — unlock to explore scenarios.")

        st.slider("Days", 1, 60, key=k("days"))

    with c2:
        st.number_input("Adults", 1, 10, key=k("adults"))
    with c3:
        st.number_input("Kids", 0, 10, key=k("kids"))

    days = int(st.session_state[k("days")])
    adults = int(st.session_state[k("adults")])
    kids = int(st.session_state[k("kids")])

    # Sidebar-ish controls (inline)
    top_left, top_right = st.columns([1.4, 1.0])
    with top_left:
        st.markdown("#### 🧠 Travel style")
        st.caption("Choose how you typically allocate your budget while travelling.")
        cur_style = st.session_state.get(k("travel_style"), "Balanced")
        if cur_style not in TRAVEL_STYLES:
            cur_style = "Balanced"

        # Ensure widget has a valid current value without using index (avoids yellow warning)
        if k("style_select") not in st.session_state:
            st.session_state[k("style_select")] = cur_style
        elif st.session_state[k("style_select")] not in TRAVEL_STYLES:
            st.session_state[k("style_select")] = "Balanced"

        st.selectbox(
            "Travel style",
            TRAVEL_STYLES,
            key=k("style_select"),
            on_change=on_style_change,
            args=(prices_df,),
            label_visibility="collapsed",
        )

    with top_right:
        st.markdown("#### 🎯 Cost scenario")
        st.caption("Controls how conservative the estimate is by choosing lower, average, or upper typical prices.")
        st.radio(
            "Cost scenario",
            COST_SCENARIOS,
            key=k("cost_scenario"),
            horizontal=True,
            label_visibility="collapsed",
        )

        st.session_state[k("advanced_mode")] = st.checkbox(
            "Advanced mode",
            value=bool(st.session_state.get(k("advanced_mode"), False)),
            key=k("adv_checkbox"),
        )

    # Auto accommodation proxy (default only)
    set_accommodation_proxy_by_people(adults=adults, kids=kids)

    # Category dials
    st.markdown("#### 🎛️ Category dials")
    st.caption("Reference amounts describe a typical traveller. Spending levels scale these assumptions to produce the final amounts used for cost calculation.")

    cols = st.columns(5)
    for i, cat in enumerate(CATEGORY_ORDER):
        with cols[i]:
            # title row: name + ❓ popover (saves space)
            c_name, c_info = st.columns([0.82, 0.18], vertical_alignment="center")
            with c_name:
                st.markdown(f"**{cat}**")
            with c_info:
                with st.popover("❓"):
                    st.markdown(CATEGORY_EXPLANATIONS.get(cat, ""))

            # Ensure the widget key exists BEFORE widget is created (no 'value=' needed)
            if k(f"dial_label_{cat}") not in st.session_state or st.session_state[k(f"dial_label_{cat}")] not in DIAL_LABELS:
                st.session_state[k(f"dial_label_{cat}")] = "Typical"

            st.select_slider(
                "Spending level",
                options=DIAL_LABELS,
                key=k(f"dial_label_{cat}"),
                on_change=on_dial_change,
                args=(cat,),
                label_visibility="collapsed",
            )

    # Advanced: edit base quantities
    if st.session_state.get(k("advanced_mode"), False):
        st.markdown("#### 🧰 Advanced: Edit reference amounts")
        st.caption("Setting a reference amount to 0 explicitly excludes an item from your trip.")

        plan_df = st.session_state[k("plan_df")]

        for cat in CATEGORY_ORDER:
            with st.expander(f"Edit items: {cat}", expanded=False):
                cat_df = plan_df[plan_df["category"] == cat].copy()
                if cat_df.empty:
                    st.info("No items.")
                    continue

                for idx in cat_df.index:
                    row = plan_df.loc[idx]
                    left, right = st.columns([2.2, 1.0])
                    with left:
                        st.write(f"**{row.get('item_name_short', row.get('pattern'))}**")
                        st.caption(f"{row.get('unit_type')}")

                    with right:
                        # Accommodation: integer only, but allow 0 (camper/relatives)
                        is_acc = (cat == "Accommodation")

                        if is_acc:
                            cur_val = int(round(float(row.get("base_qty", 0.0))))
                            new_val = st.number_input(
                                "Reference amount",
                                min_value=0,
                                max_value=12,
                                value=cur_val,
                                step=1,
                                key=k(f"base_{cat}_{idx}"),
                                on_change=mark_customised,
                            )
                            plan_df.loc[idx, "base_qty"] = float(int(new_val))
                        else:
                            cur_val = float(row.get("base_qty", 0.0))
                            new_val = st.number_input(
                                "Reference amount",
                                min_value=0.0,
                                max_value=999.0,
                                value=float(cur_val),
                                step=0.05,
                                key=k(f"base_{cat}_{idx}"),
                                on_change=mark_customised,
                            )
                            plan_df.loc[idx, "base_qty"] = float(new_val)

        st.session_state[k("plan_df")] = plan_df

    # Compute
    price_col = SCENARIO_TO_PRICE_COL.get(st.session_state.get(k("cost_scenario"), "Average"), "average_price")

    detailed, cat_local, cat_eur, local_currency = compute_costs(
        prices_df=prices_df,
        plan_df=st.session_state[k("plan_df")],
        exchange_df=exchange_df,
        price_col=price_col,
        days=days,
        adults=adults,
        kids=kids,
        category_dials=st.session_state[k("category_dials")],
    )

    symbol_local = f"{local_currency} " if local_currency else ""
    symbol_eur = "€ "
    rate = get_rate_eur_to_currency(exchange_df, local_currency) if local_currency else None

    missing_categories = [cat for cat in CATEGORY_ORDER if not category_has_any_price_data(detailed, cat)]

    # Summary
    st.markdown("#### 🧾 Summary")
    total_local = sum(cat_local.values()) if cat_local else 0.0
    total_eur = sum(cat_eur.values()) if cat_eur else (total_local / rate if rate else None)

    l, m, r = st.columns([1.1, 1.1, 1.8])
    with l:
        st.metric("Total (local)", money(total_local, symbol_local))
        st.caption(f"Currency: **{local_currency or 'Unknown'}**")
    with m:
        st.metric("Total (EUR)", money(total_eur, symbol_eur) if total_eur is not None else "—")
        if rate:
            st.caption(f"1 EUR = {rate:.4f} {local_currency}")
        else:
            st.caption("No exchange rate found for this currency.")
    with r:
        persons = max(adults + kids, 1)
        per_person_day_local = (total_local / max(days, 1)) / persons
        st.write("**Sanity checks**")
        st.write(f"Per person per day (local): **{money(per_person_day_local, symbol_local)}**")
        if rate:
            st.write(f"Per person per day (EUR): **{money(per_person_day_local / rate, symbol_eur)}**")
        if missing_categories:
            st.warning(
                "Some categories are excluded because Numbeo price data is missing for this country: "
                + ", ".join(missing_categories)
            )

    # Category breakdown
    st.markdown("#### 🧩 Category Breakdown")
    cards = st.columns(5)
    for i, cat in enumerate(CATEGORY_ORDER):
        with cards[i]:
            st.markdown(f"**{cat}**")
            if not category_has_any_price_data(detailed, cat):
                st.write("No data available")
                st.write("—")
            else:
                local_val = cat_local.get(cat, None)
                eur_val = cat_eur.get(cat, None)
                st.write(money(float(local_val), symbol_local) if local_val is not None else "—")
                st.write(money(float(eur_val), symbol_eur) if eur_val is not None else "—")

            if st.session_state.get(k("advanced_mode"), False):
                label = st.session_state.get(k(f"dial_label_{cat}"), "Typical")
                mult = float(st.session_state[k("category_dials")].get(cat, 1.0))
                st.caption(f"{label} • x{mult:.2f}")

    # Details (Advanced always shows, otherwise optional)
    show_details = st.session_state.get(k("advanced_mode"), False) or st.checkbox("Show item details", value=False, key=k("show_details"))
    if show_details:
        st.markdown("#### 🔍 Item details")

        st.info(
            "Reference amounts describe a typical traveller. Spending multipliers scale these assumptions. "
            "Trip quantity is the final quantity used for pricing after applying trip length and group size."
        )

        # Accommodation-only comment (ONLY here, as requested)
        st.caption(
            "**Accommodation note:** Apartment rent is a *monthly* price. Trip quantity can be below 1 (e.g., 0.60) "
            "because we scale monthly rent by (days / 30)."
        )

        view_cols = [
            "item",
            "reference_amount",
            "spending_multiplier",
            "final_amount",
            "trip_quantity",
            "unit_type",
            "unit_price_local",
            "total_local",
            "total_eur",
        ]
        rename = {
            "item": "Item",
            "reference_amount": "Reference amount",
            "spending_multiplier": "Spending multiplier",
            "final_amount": "Final amount",
            "trip_quantity": "Trip quantity",
            "unit_type": "Unit",
            "unit_price_local": "Price per unit (local)",
            "total_local": "Total (local)",
            "total_eur": "Total (EUR)",
        }

        for cat in CATEGORY_ORDER:
            with st.expander(f"{cat} — items", expanded=False):
                sub = detailed[detailed["category"] == cat].copy()
                if sub.empty:
                    st.info("No items.")
                    continue
                if not category_has_any_price_data(detailed, cat):
                    st.info("No price data available for this category in the selected country.")

                # nicer rounding
                def r2(x):
                    if x is None or (isinstance(x, float) and pd.isna(x)):
                        return None
                    return round(float(x), 2)

                sub["reference_amount"] = sub["reference_amount"].apply(r2)
                sub["spending_multiplier"] = sub["spending_multiplier"].apply(r2)
                sub["final_amount"] = sub["final_amount"].apply(r2)
                sub["trip_quantity"] = sub["trip_quantity"].apply(r2)
                sub["unit_price_local"] = sub["unit_price_local"].apply(r2)
                sub["total_local"] = sub["total_local"].apply(r2)
                sub["total_eur"] = sub["total_eur"].apply(r2)

                st.dataframe(sub[view_cols].rename(columns=rename), use_container_width=True)

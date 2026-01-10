import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional

# ============================================================
# Config
# ============================================================
st.set_page_config(page_title="Trip Cost Estimator (Numbeo)", page_icon="💸", layout="wide")
DEFAULT_DB = "unified_country_database.db"

CATEGORY_ORDER = ["Food & Drinks", "Accommodation", "Local Transport", "Entertainment", "Shopping & Souvenirs"]

# ============================================================
# DB helpers (cache by db_path string, NOT connection)
# ============================================================
def resolve_db_path(db_name: str = DEFAULT_DB) -> str:
    here = Path(__file__).parent
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
def load_countries(db_path: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        try:
            df = pd.read_sql(
                "SELECT DISTINCT iso3, country_name FROM countries WHERE iso3 IS NOT NULL AND country_name IS NOT NULL",
                conn,
            )
            if not df.empty:
                return df.sort_values("country_name").reset_index(drop=True)
        except Exception:
            pass

        df = pd.read_sql(
            "SELECT DISTINCT iso3, country_name FROM numbeo_prices WHERE iso3 IS NOT NULL AND country_name IS NOT NULL",
            conn,
        )
        return df.sort_values("country_name").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_exchange_rates(db_path: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(
            "SELECT currency, one_eur_to_currency, one_usd_to_currency FROM numbeo_exchange_rates",
            conn,
        )
    return df


@st.cache_data(show_spinner=False)
def load_country_prices(db_path: str, iso3: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
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
            params=(iso3,),
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
        return f"{prefix}{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{prefix}{x}"


def clear_widget_keys(prefixes: Tuple[str, ...]) -> None:
    """Delete widget keys so Streamlit doesn't keep stale widget state after resets."""
    to_delete = [k for k in list(st.session_state.keys()) if any(k.startswith(p) for p in prefixes)]
    for k in to_delete:
        try:
            del st.session_state[k]
        except Exception:
            pass


# ============================================================
# Defaults / Presets (UPDATED BASE LEVELS)
# ============================================================
DEFAULT_ITEMS = {
    "Food & Drinks": [
        ("Meal at an Inexpensive Restaurant", "per_person_per_day", 1.00),  # was 0.70
        ("Cappuccino", "per_person_per_day", 0.70),  # was 0.50
        ("Soft Drink (Coca-Cola or Pepsi", "per_person_per_day", 0.40),  # was 0.30
        ("Bottled Water (0.33 Liter)", "per_person_per_day", 1.00),  # was 0.80
        ("Domestic Draft Beer (0.5 Liter)", "per_person_per_day", 0.30),  # was 0.25
        ("Imported Beer (0.33 Liter Bottle)", "per_person_per_day", 0.20),  # was 0.15
    ],
    "Local Transport": [
        ("One-Way Ticket (Local Transport)", "per_person_per_day", 1.50),  # was 1.20
        ("Taxi Start (Standard Tariff)", "per_trip", 1.50),
        ("Taxi 1 km (Standard Tariff)", "per_km", 10.00),  # was 8.00
        ("Monthly Public Transport Pass", "per_person_per_month", 0.00),
    ],
    "Entertainment": [
        ("Cinema Ticket (International Release)", "per_person_per_week", 2.00),
        ("Monthly Fitness Club Membership", "per_person_per_month", 0.30),
        ("Tennis Court Rental (1 Hour, Weekend)", "per_person_per_week", 0.50),  # was 0.10
    ],
    "Shopping & Souvenirs": [
        ("Jeans (Levi's 501", "per_item", 0.40),
        ("Summer Dress in a Chain Store", "per_item", 0.40),
        ("Nike Running Shoes", "per_item", 0.30),
    ],
    "Accommodation": [
        ("1 Bedroom Apartment in City Centre", "per_month_household", 1),
        ("3 Bedroom Apartment in City Centre", "per_month_household", 0),
    ],
}

DIAL_LABELS = ["Minimal", "Budget", "Typical", "Comfortable", "Premium"]
LABEL_TO_DIAL = {"Minimal": 0.15, "Budget": 0.60, "Typical": 1.00, "Comfortable": 1.60, "Premium": 2.50}

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
SCENARIO_TO_PRICE_COL = {"Optimistic": "lowest_price", "Average": "average_price", "Conservative": "highest_price"}

CATEGORY_EXPLANATIONS = {
    "Food & Drinks": (
        "Estimates daily spending on food and beverages, anchored on inexpensive local restaurant meals plus everyday drinks. "
        "Restaurant prices can also serve as a proxy for grocery based cooking, since food costs tend to move together across countries."
    ),
    "Accommodation": (
        "Approximates housing costs using average city centre apartment rents scaled to your trip length. "
        "In Advanced mode you can set accommodation to 0 (friends/camper) or combine multiple apartments (split stay)."
    ),
    "Local Transport": (
        "Captures local mobility costs such as public transport and taxis, reflecting typical travel within the city during your stay."
    ),
    "Entertainment": (
        "Represents optional leisure spending using common price anchors such as cinema, fitness, and sports services as a proxy for overall leisure costs."
    ),
    "Shopping & Souvenirs": (
        "Estimates incidental and discretionary spending using stable international price anchors such as common clothing items."
    ),
}


# ============================================================
# Matching items in DB (regex=False)
# ============================================================
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

    return 1.0


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
):
    """
    Final amount = Reference amount × Spending multiplier × Trip scaling
    """
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
        reference_amount = clamp_nonneg(r.get("base_qty", 0.0))

        unit_mult = compute_unit_multiplier(unit_type, days, adults, kids)
        final_amount = float(reference_amount) * float(dial) * float(unit_mult)

        total_local = None
        if price_val is not None and not pd.isna(price_val):
            total_local = float(price_val) * float(final_amount)

        rate = get_rate_eur_to_currency(exchange_df, local_currency)
        total_eur = None
        if total_local is not None and rate is not None:
            total_eur = float(total_local) / float(rate)

        out_rows.append(
            {
                "category": cat,
                "item": r.get("item_name_short", r.get("pattern", "")),
                "reference_amount": float(reference_amount),
                "spending_multiplier": float(dial),
                "final_amount": float(final_amount),
                "unit_type": unit_type,
                "unit_price_local": None if price_val is None or pd.isna(price_val) else float(price_val),
                "total_local": total_local,
                "total_eur": total_eur,
                "missing_price": (price_val is None or pd.isna(price_val)),
            }
        )

    detailed = pd.DataFrame(out_rows)
    cat_local = detailed.dropna(subset=["total_local"]).groupby("category")["total_local"].sum().to_dict()
    cat_eur = detailed.dropna(subset=["total_eur"]).groupby("category")["total_eur"].sum().to_dict()

    return detailed, cat_local, cat_eur, local_currency


# ============================================================
# Session state + style logic
# ============================================================
def ensure_state_defaults():
    st.session_state.setdefault("db_path", resolve_db_path(DEFAULT_DB))
    st.session_state.setdefault("iso3", None)

    st.session_state.setdefault("days", 7)
    st.session_state.setdefault("adults", 2)
    st.session_state.setdefault("kids", 0)

    st.session_state.setdefault("style_select", "Balanced")
    st.session_state.setdefault("pending_style", None)

    st.session_state.setdefault("_applying_style", False)
    st.session_state.setdefault("advanced_mode", False)
    st.session_state.setdefault("cost_scenario", "Average")

    st.session_state.setdefault("advanced_dirty", False)
    st.session_state.setdefault("acc_manual", False)

    st.session_state.setdefault("category_dials", {c: 1.0 for c in CATEGORY_ORDER})
    for cat in CATEGORY_ORDER:
        st.session_state.setdefault(f"dial_label_{cat}", "Typical")

    st.session_state.setdefault("default_plan_df", None)
    st.session_state.setdefault("plan_df", None)


def apply_pending_style_if_any():
    """Run before sidebar widgets are created (safe way to switch selectbox value)."""
    if st.session_state.get("pending_style"):
        st.session_state["style_select"] = st.session_state["pending_style"]
        st.session_state["pending_style"] = None


def build_or_refresh_country_plans(prices_df: pd.DataFrame):
    default_plan = build_default_plan(prices_df)
    st.session_state.default_plan_df = default_plan
    st.session_state.plan_df = default_plan.copy(deep=True)
    st.session_state.advanced_dirty = False
    st.session_state.acc_manual = False
    clear_widget_keys(("base_",))


def reset_active_plan_to_default():
    if st.session_state.default_plan_df is None or st.session_state.default_plan_df.empty:
        return
    st.session_state.plan_df = st.session_state.default_plan_df.copy(deep=True)
    st.session_state.advanced_dirty = False
    st.session_state.acc_manual = False
    clear_widget_keys(("base_",))


def set_accommodation_proxy_by_people(adults: int, kids: int):
    if st.session_state.get("acc_manual", False):
        return
    if st.session_state.plan_df is None or st.session_state.plan_df.empty:
        return

    persons = int(adults) + int(kids)
    use_3br = persons >= 3

    plan = st.session_state.plan_df
    acc_rows = plan[plan["category"] == "Accommodation"].copy()
    if acc_rows.empty:
        return

    idx_1br = None
    idx_3br = None
    for idx, r in acc_rows.iterrows():
        pat = str(r["pattern"])
        if "1 Bedroom Apartment in City Centre" in pat:
            idx_1br = idx
        elif "3 Bedroom Apartment in City Centre" in pat:
            idx_3br = idx

    for idx in [idx_1br, idx_3br]:
        if idx is not None:
            st.session_state.plan_df.loc[idx, "base_qty"] = 0

    if use_3br and idx_3br is not None:
        st.session_state.plan_df.loc[idx_3br, "base_qty"] = 1
    elif idx_1br is not None:
        st.session_state.plan_df.loc[idx_1br, "base_qty"] = 1


def apply_style_to_dials(style: str):
    if style not in STYLE_DEFAULT_LABELS:
        return

    if st.session_state.get("advanced_dirty", False) or st.session_state.get("acc_manual", False):
        reset_active_plan_to_default()

    st.session_state._applying_style = True

    labels = STYLE_DEFAULT_LABELS[style]
    for cat in CATEGORY_ORDER:
        label = labels.get(cat, "Typical")
        st.session_state[f"dial_label_{cat}"] = label
        st.session_state.category_dials[cat] = LABEL_TO_DIAL.get(label, 1.0)

    st.session_state._applying_style = False


def request_customised_switch():
    if st.session_state.get("_applying_style", False):
        return
    st.session_state["pending_style"] = "Customised"


def on_style_change():
    style = st.session_state.get("style_select", "Balanced")
    if style in STYLE_DEFAULT_LABELS:
        apply_style_to_dials(style)


def on_dial_change(cat: str):
    label = st.session_state.get(f"dial_label_{cat}", "Typical")
    st.session_state.category_dials[cat] = LABEL_TO_DIAL.get(label, 1.0)
    request_customised_switch()


def mark_advanced_changed(is_accommodation: bool = False):
    if st.session_state.get("_applying_style", False):
        return
    st.session_state.advanced_dirty = True
    if is_accommodation:
        st.session_state.acc_manual = True
    request_customised_switch()


def category_has_any_price_data(detailed: pd.DataFrame, cat: str) -> bool:
    sub = detailed[detailed["category"] == cat]
    if sub.empty:
        return False
    return sub["total_local"].notna().any() or sub["total_eur"].notna().any()


# ============================================================
# Details table columns
# ============================================================
DETAIL_COLS = [
    "item",
    "reference_amount",
    "spending_multiplier",
    "final_amount",
    "unit_price_local",
    "total_local",
    "total_eur",
]
DETAIL_COL_RENAME = {
    "item": "Item",
    "reference_amount": "Reference amount",
    "spending_multiplier": "Spending multiplier",
    "final_amount": "Final amount",
    "unit_price_local": "Price per unit (local)",
    "total_local": "Total (local)",
    "total_eur": "Total (EUR)",
}


# ============================================================
# Main App
# ============================================================
def main():
    ensure_state_defaults()
    apply_pending_style_if_any()

    st.markdown("## 💸 Trip Cost Estimator (Numbeo)")
    st.caption("Days + persons + travel style. Prices from `numbeo_prices`. Conversion from `numbeo_exchange_rates`.")

    # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 Data Source")
        st.session_state.db_path = st.text_input("SQLite DB path", value=st.session_state.db_path)

        countries_df = load_countries(st.session_state.db_path)
        if countries_df.empty:
            st.error("No countries found. Check DB path and tables.")
            st.stop()

        options = countries_df["country_name"].tolist()
        default_idx = 0
        if st.session_state.iso3:
            hit = countries_df.index[countries_df["iso3"] == st.session_state.iso3]
            if len(hit) > 0:
                default_idx = int(hit[0])

        country_name = st.selectbox("Country", options, index=default_idx, key="country_name_select")
        iso3 = countries_df.loc[countries_df["country_name"] == country_name, "iso3"].iloc[0]
        changed_country = (st.session_state.iso3 != iso3)
        st.session_state.iso3 = iso3

        st.markdown("---")

        st.markdown("### 🧠 Travel style")
        st.caption("Choose how you typically allocate your budget while travelling.")
        st.selectbox("Travel style", TRAVEL_STYLES, key="style_select", on_change=on_style_change)

        st.markdown("---")

        st.markdown("### 🎯 Cost scenario")
        st.caption("Controls how conservative the estimate is by choosing lower, average, or upper typical prices.")
        st.radio("Cost scenario", COST_SCENARIOS, key="cost_scenario")

        st.markdown("---")
        st.session_state.advanced_mode = st.checkbox("Advanced mode", value=st.session_state.advanced_mode, key="adv_checkbox")

        if st.session_state.get("advanced_dirty", False):
            st.caption("Advanced adjustments are active. Selecting a preset resets them immediately.")

    prices_df = load_country_prices(st.session_state.db_path, st.session_state.iso3)
    exchange_df = load_exchange_rates(st.session_state.db_path)

    if prices_df.empty:
        st.warning("No `numbeo_prices` for this ISO3.")
        st.stop()

    if st.session_state.plan_df is None or changed_country or st.session_state.default_plan_df is None:
        build_or_refresh_country_plans(prices_df)
        if st.session_state.style_select in STYLE_DEFAULT_LABELS:
            apply_style_to_dials(st.session_state.style_select)

    # Trip setup
    st.markdown("### 🧳 Trip Setup")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.slider("Days", 1, 60, key="days")
    with c2:
        st.number_input("Adults", 1, 10, key="adults")
    with c3:
        st.number_input("Kids", 0, 10, key="kids")

    days = int(st.session_state.days)
    adults = int(st.session_state.adults)
    kids = int(st.session_state.kids)

    set_accommodation_proxy_by_people(adults=adults, kids=kids)

    # Category dials
    st.markdown("### 🎛️ Category dials")
    st.caption("Adjust how much you spend in each category. Manual changes switch travel style to Customised.")

    cols = st.columns(5)
    for i, cat in enumerate(CATEGORY_ORDER):
        with cols[i]:
            st.markdown(f"**{cat}**")
            st.caption(CATEGORY_EXPLANATIONS.get(cat, ""))

            st.select_slider(
                "Spending level (scales quantities)",
                options=DIAL_LABELS,
                key=f"dial_label_{cat}",
                on_change=on_dial_change,
                args=(cat,),
            )

    # Advanced
    if st.session_state.advanced_mode:
        st.markdown("### 🧰 Advanced: Edit reference amounts")
        st.caption("Set to 0 if an item does not apply to your trip. Accommodation can be 0 (friends/camper) or both > 0 (split stay).")

        for cat in CATEGORY_ORDER:
            with st.expander(f"Edit items: {cat}", expanded=False):
                cat_df = st.session_state.plan_df[st.session_state.plan_df["category"] == cat].copy()
                if cat_df.empty:
                    st.info("No items.")
                    continue

                for idx in cat_df.index:
                    row = st.session_state.plan_df.loc[idx]
                    a, b = st.columns([2.2, 1.0])

                    with a:
                        st.write(f"**{row.get('item_name_short', row.get('pattern'))}**")
                        st.caption(f"{row.get('unit_type')}")

                    with b:
                        if cat == "Accommodation":
                            current = int(row.get("base_qty", 0) or 0)
                            new_val = st.number_input(
                                "Reference amount",
                                min_value=0,
                                max_value=10,
                                value=current,
                                step=1,
                                key=f"base_{cat}_{idx}",
                                on_change=mark_advanced_changed,
                                args=(True,),
                            )
                            st.session_state.plan_df.loc[idx, "base_qty"] = int(new_val)
                        else:
                            new_val = st.number_input(
                                "Reference amount",
                                min_value=0.0,
                                max_value=999.0,
                                value=float(row.get("base_qty", 0.0)),
                                step=0.05,
                                key=f"base_{cat}_{idx}",
                                on_change=mark_advanced_changed,
                                args=(False,),
                            )
                            st.session_state.plan_df.loc[idx, "base_qty"] = float(new_val)

    # Compute
    price_col = SCENARIO_TO_PRICE_COL.get(st.session_state.cost_scenario, "average_price")

    detailed, cat_local, cat_eur, local_currency = compute_costs(
        prices_df=prices_df,
        plan_df=st.session_state.plan_df,
        exchange_df=exchange_df,
        price_col=price_col,
        days=days,
        adults=adults,
        kids=kids,
        category_dials=st.session_state.category_dials,
    )

    symbol_local = f"{local_currency} "
    symbol_eur = "€ "
    rate = get_rate_eur_to_currency(exchange_df, local_currency)

    def cat_has_data(cat: str) -> bool:
        return category_has_any_price_data(detailed, cat)

    missing_categories = [cat for cat in CATEGORY_ORDER if not cat_has_data(cat)]

    # Summary
    st.markdown("### 🧾 Summary")
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

    # Category Breakdown
    st.markdown("### 🧩 Category Breakdown")
    cards = st.columns(5)
    for i, cat in enumerate(CATEGORY_ORDER):
        with cards[i]:
            st.markdown(f"**{cat}**")
            if not cat_has_data(cat):
                st.write("No data available")
                st.write("—")
            else:
                local_val = cat_local.get(cat, None)
                eur_val = cat_eur.get(cat, None)
                st.write(money(float(local_val), symbol_local) if local_val is not None else "—")
                st.write(money(float(eur_val), symbol_eur) if eur_val is not None else "—")

            if st.session_state.advanced_mode:
                label = st.session_state.get(f"dial_label_{cat}", "Typical")
                mult = float(st.session_state.category_dials.get(cat, 1.0))
                st.caption(f"{label} • x{mult:.2f}")

    # Details
    show_details = st.session_state.advanced_mode or st.checkbox("Show item details", value=False)
    if show_details:
        st.markdown("### 🔍 Item details")
        st.caption(
            "Reference amounts describe a typical traveller. "
            "Spending multipliers scale these assumptions to produce the final amounts used for cost calculation."
        )

        for cat in CATEGORY_ORDER:
            with st.expander(f"{cat} — items", expanded=False):
                sub = detailed[detailed["category"] == cat].copy()
                if sub.empty:
                    st.info("No items.")
                    continue
                if not cat_has_data(cat):
                    st.info("No price data available for this category in the selected country.")

                if cat == "Accommodation":
                    st.caption(
                        f"Note: Accommodation prices are monthly rents. The model scales them by trip length (days/30). "
                        f"For example, {days} days ≈ {days/30:.2f} months, so the final amount can be fractional."
                    )

                sub["reference_amount"] = sub["reference_amount"].apply(lambda x: round(float(x), 2))
                sub["spending_multiplier"] = sub["spending_multiplier"].apply(lambda x: round(float(x), 2))
                sub["final_amount"] = sub["final_amount"].apply(lambda x: round(float(x), 2))
                sub["unit_price_local"] = sub["unit_price_local"].apply(lambda x: None if x is None else round(float(x), 2))
                sub["total_local"] = sub["total_local"].apply(lambda x: None if x is None else round(float(x), 2))
                sub["total_eur"] = sub["total_eur"].apply(lambda x: None if x is None else round(float(x), 2))

                view = sub[
                    ["item", "reference_amount", "spending_multiplier", "final_amount", "unit_price_local", "total_local", "total_eur"]
                ].rename(columns={
                    "item": "Item",
                    "reference_amount": "Reference amount",
                    "spending_multiplier": "Spending multiplier",
                    "final_amount": "Final amount",
                    "unit_price_local": "Price per unit (local)",
                    "total_local": "Total (local)",
                    "total_eur": "Total (EUR)",
                })
                st.dataframe(view, use_container_width=True)


if __name__ == "__main__":
    main()

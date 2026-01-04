import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import random
import datetime
import time
import os
import json
import re
import base64
from dotenv import load_dotenv
from openai import OpenAI
import amadeus_api_client as amadeus
import google_calendar_client as calendar_client
import requests

# =============================
# CONFIG
# =============================
load_dotenv()
st.set_page_config(page_title="Global Travel Planner", page_icon="🌏", layout="wide")

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8501"


@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)


client = get_openai_client()

# =============================
# STYLES
# =============================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

        html, body, .stMarkdown, div[data-testid="stText"], .stButton button {
            font-family: 'Poppins', sans-serif !important;
            color: var(--text-color);
        }

        .main-header {
            font-size: 3rem;
            color: #1a237e;
            font-weight: 700;
            text-align: center;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            text-align: center;
            color: #666;
            font-size: 1.2rem;
            margin-bottom: 3rem;
        }

        @media (prefers-color-scheme: dark) {
            .main-header { color: #2949FF; }
            .sub-header { color: #A1A1A1; }
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
        }

        .price-text { color: var(--primary-color); font-size: 1.4rem; font-weight: 700; }
        .carrier-text { font-size: 1.1rem; font-weight: 600; color: var(--text-color); }
        .route-text { color: var(--text-color); opacity: 0.7; font-size: 0.9rem; }

        .swipe-card {
            text-align: center;
            padding: 2rem;
            border: 2px dashed #e0e0e0;
            border-radius: 15px;
            background-color: #fafafa;
        }
        .swipe-card h3 { color: #333; margin-bottom: 2rem; }
        .swipe-icon { font-size: 4rem; display: block; margin-bottom: 1rem; }

        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            font-weight: 600;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        div[data-testid="stButton"] > button {
            background-color: #1a237e;
            color: white;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #283593;
            color: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# WEIGHTS / HELP TEXTS
# =============================

# Numbeo safety removed: safety uses TuGo only
WEIGHT_KEYS = [
    "safety_tugo",
    "cost", "restaurant", "groceries", "rent",
    "purchasing_power",
    "qol", "health_care", "clean_air",
    "culture", "weather",
    "luxury_price",
    "hidden_gem", "astro", "jitter",
]

SLIDER_HELP = {
    "safety_tugo": "Prioritizes destinations with lower official travel risk based on travel advisories.",
    "cost": "Favors destinations where everyday life is cheaper overall.",
    "restaurant": "Prefers countries where eating out is relatively affordable.",
    "groceries": "Prioritizes destinations with lower supermarket and grocery costs.",
    "rent": "Favors countries with lower rental prices, especially for longer stays.",
    "purchasing_power": "Prefers places where local income has stronger purchasing power.",
    "qol": "Prioritizes destinations with higher overall living standards.",
    "health_care": "Favors countries with stronger and more accessible healthcare systems.",
    "clean_air": "Prioritizes destinations with lower pollution and better air quality.",
    "culture": "Prefers countries rich in cultural heritage and historical sites.",
    "weather": "Prioritizes destinations whose average climate matches your preferred temperature.",
    "luxury_price": "Allows more expensive destinations to rank higher if they offer a premium or luxury experience.",
    "hidden_gem": "Adds a preference for less obvious, off-the-radar destinations.",
    "astro": "Adds a playful, astrology-based influence to the ranking.",
    "jitter": "Introduces controlled randomness to diversify otherwise similar results.",
}

# =============================
# SMALL HELPERS
# =============================

def safe_median(s: pd.Series, default: float) -> float:
    s = pd.to_numeric(s, errors="coerce")
    if s.notna().any():
        return float(s.median())
    return float(default)


def clamp_int(v, lo=0, hi=100) -> int:
    try:
        v = int(round(float(v)))
    except Exception:
        v = 0
    return int(max(lo, min(hi, v)))


def normalize_weights_100(weights: dict) -> dict:
    """
    Ensure full WEIGHT_KEYS dict of ints that sums to exactly 100.
    If all are 0 -> defaults to cost=100 (safe fallback).
    """
    w = {k: clamp_int(weights.get(k, 0)) for k in WEIGHT_KEYS}
    total = sum(w.values())
    if total <= 0:
        w = {k: 0 for k in WEIGHT_KEYS}
        w["cost"] = 100
        return w

    scaled = {k: (w[k] / total) * 100.0 for k in WEIGHT_KEYS}
    w_int = {k: int(round(scaled[k])) for k in WEIGHT_KEYS}

    drift = 100 - sum(w_int.values())
    if drift != 0:
        k_star = max(w_int, key=lambda kk: w_int[kk])
        w_int[k_star] = clamp_int(w_int[k_star] + drift)

    # final guard
    total2 = sum(w_int.values())
    if total2 != 100:
        k_star = max(w_int, key=lambda kk: w_int[kk])
        w_int[k_star] = clamp_int(w_int[k_star] + (100 - total2))

    return w_int


def set_adv_from_weights(weights_100: dict):
    """
    Writes persona weights into adv_* session keys.
    IMPORTANT: call this only BEFORE slider widgets are created in the current run.
    """
    w = normalize_weights_100(weights_100)
    for k in WEIGHT_KEYS:
        st.session_state[f"adv_{k}"] = int(w.get(k, 0))


def _largest_remainder_allocation(shares_float: dict, total_points: int, caps: dict | None = None) -> dict:
    """
    Allocate integer points summing to total_points based on float shares (largest remainder).
    caps (optional): per-key max allocation.
    """
    if total_points <= 0:
        return {k: 0 for k in shares_float.keys()}

    denom = sum(max(0.0, float(v)) for v in shares_float.values())
    keys = list(shares_float.keys())

    if denom <= 0:
        base = total_points // len(keys)
        extra = total_points % len(keys)
        out = {k: base for k in keys}
        for k in keys[:extra]:
            out[k] += 1
        if caps:
            return _apply_caps_and_redistribute(out, caps, total_points)
        return out

    raw = {k: total_points * (max(0.0, float(v)) / denom) for k, v in shares_float.items()}
    flo = {k: int(raw[k] // 1) for k in raw}
    rem = {k: raw[k] - flo[k] for k in raw}

    out = flo.copy()
    left = total_points - sum(out.values())

    for k in sorted(rem.keys(), key=lambda kk: rem[kk], reverse=True):
        if left <= 0:
            break
        out[k] += 1
        left -= 1

    if caps:
        out = _apply_caps_and_redistribute(out, caps, total_points)

    # drift guard
    drift = total_points - sum(out.values())
    if drift != 0:
        if drift > 0:
            for k in keys:
                if drift == 0:
                    break
                cap = caps.get(k, 10**9) if caps else 10**9
                if out[k] < cap:
                    add = min(drift, cap - out[k])
                    out[k] += add
                    drift -= add
        else:
            drift_abs = -drift
            for k in sorted(keys, key=lambda kk: out[kk], reverse=True):
                if drift_abs == 0:
                    break
                take = min(drift_abs, out[k])
                out[k] -= take
                drift_abs -= take

    return out


def _apply_caps_and_redistribute(out: dict, caps: dict, total_points: int) -> dict:
    """
    Clamp to caps and redistribute overflow into keys with headroom.
    """
    out = out.copy()
    while True:
        overflow = 0
        for k, v in out.items():
            cap = int(caps.get(k, 10**9))
            if v > cap:
                overflow += (v - cap)
                out[k] = cap

        if overflow <= 0:
            break

        headroom = [k for k, v in out.items() if out[k] < int(caps.get(k, 10**9))]
        if not headroom:
            break

        shares = {k: float(out[k] + 1) for k in headroom}
        add = _largest_remainder_allocation(
            shares,
            overflow,
            caps={k: int(caps[k]) - out[k] for k in headroom},
        )
        for k in headroom:
            out[k] += int(add.get(k, 0))

    drift = total_points - sum(out.values())
    if drift != 0:
        keys = list(out.keys())
        if drift > 0:
            for k in keys:
                if drift == 0:
                    break
                cap = int(caps.get(k, 10**9))
                if out[k] < cap:
                    out[k] += 1
                    drift -= 1
        else:
            drift_abs = -drift
            for k in sorted(keys, key=lambda kk: out[kk], reverse=True):
                if drift_abs == 0:
                    break
                if out[k] > 0:
                    out[k] -= 1
                    drift_abs -= 1
    return out


def enforce_sum_100_proportional(changed_key: str):
    """
    Keeps sum exactly 100:
    - changed_key stays fixed
    - only delta is redistributed across other ACTIVE (>0) sliders
    - redistribution is proportional to current values (keeps the existing balance)
    - 0 stays 0 (not automatically activated)
    - if user kills the last active slider -> changed_key becomes 100
    """
    keys = WEIGHT_KEYS
    if changed_key not in keys:
        return

    cur = {k: clamp_int(st.session_state.get(f"adv_{k}", 0)) for k in keys}
    total = sum(cur.values())

    # avoid all-zero state
    if total <= 0:
        for k in keys:
            st.session_state[f"adv_{k}"] = 0
        st.session_state[f"adv_{changed_key}"] = 100
        return

    if total == 100:
        return

    fixed = cur[changed_key]
    others = [k for k in keys if k != changed_key]
    candidates = [k for k in others if cur[k] > 0]  # only active sliders

    if not candidates:
        for k in others:
            st.session_state[f"adv_{k}"] = 0
        st.session_state[f"adv_{changed_key}"] = 100
        return

    delta = 100 - total

    if delta > 0:
        # distribute missing points proportionally to current candidate values
        add = _largest_remainder_allocation(
            {k: float(cur[k]) for k in candidates},
            delta,
            caps={k: 100 - cur[k] for k in candidates},
        )
        for k in candidates:
            cur[k] = clamp_int(cur[k] + int(add.get(k, 0)))

    else:
        # remove points proportionally without driving any candidate below 0
        remaining = -delta
        pool = candidates[:]

        while remaining > 0 and pool:
            pool_sum = sum(cur[k] for k in pool)
            if pool_sum <= 0:
                break

            rem_alloc = _largest_remainder_allocation(
                {k: float(cur[k]) for k in pool},
                remaining,
                caps={k: cur[k] for k in pool},
            )

            removed = 0
            for k in pool:
                r = int(rem_alloc.get(k, 0))
                if r > 0:
                    cur[k] = clamp_int(cur[k] - r)
                    removed += r

            remaining -= removed
            pool = [k for k in pool if cur[k] > 0]

            if removed == 0 and remaining > 0 and pool:
                k_star = max(pool, key=lambda kk: cur[kk])
                cur[k_star] = clamp_int(cur[k_star] - 1)
                remaining -= 1
                pool = [k for k in pool if cur[k] > 0]

    # enforce fixed exactly + drift correction (not touching changed_key)
    cur[changed_key] = fixed
    drift = 100 - sum(cur.values())
    if drift != 0:
        if drift > 0:
            for k in sorted(candidates, key=lambda kk: cur[kk], reverse=True):
                if drift == 0:
                    break
                if cur[k] < 100:
                    cur[k] += 1
                    drift -= 1
        else:
            drift_abs = -drift
            for k in sorted(candidates, key=lambda kk: cur[kk], reverse=True):
                if drift_abs == 0:
                    break
                if cur[k] > 0:
                    cur[k] -= 1
                    drift_abs -= 1

    if sum(cur.values()) <= 0:
        cur = {k: 0 for k in keys}
        cur[changed_key] = 100

    for k in keys:
        st.session_state[f"adv_{k}"] = int(clamp_int(cur[k]))


def slider_row(label: str, key: str):
    """
    One slider row with a small popover help.
    IMPORTANT: no 'value=' for sliders with key= (avoids Streamlit warning).
    """
    left, right = st.columns([0.88, 0.12], vertical_alignment="center")
    with left:
        st.markdown(f"**{label}**")
    with right:
        with st.popover("❓"):
            st.markdown(
                f"<div style='font-size: 1.10rem; line-height: 1.45;'>{SLIDER_HELP.get(key, '')}</div>",
                unsafe_allow_html=True,
            )

    # Ensure state exists BEFORE widget creation (prevents default+state conflict)
    st.session_state.setdefault(f"adv_{key}", 0)

    st.slider(
        label="",
        min_value=0,
        max_value=100,
        step=1,
        key=f"adv_{key}",
        label_visibility="collapsed",
        on_change=enforce_sum_100_proportional,
        args=(key,),
    )


def weights_to_unit(weights_100: dict) -> dict:
    return {k: float(clamp_int(weights_100.get(k, 0))) / 100.0 for k in WEIGHT_KEYS}


def adjust_weights_points(weights_100: dict, deltas: dict) -> dict:
    """
    Apply integer point deltas (swipes), clamp and renormalize to sum=100.
    """
    w = {k: clamp_int(weights_100.get(k, 0)) for k in WEIGHT_KEYS}
    for k, d in deltas.items():
        if k in w:
            w[k] = clamp_int(w[k] + int(d))
    return normalize_weights_100(w)

# =============================
# DATA MANAGER
# =============================
class DataManager:
    def __init__(self, db_name="unified_country_database.db"):
        self.db_path = self._find_db(db_name)

    def _find_db(self, db_name):
        current_dir = Path(__file__).parent
        paths = [current_dir / db_name, current_dir / "data" / db_name]
        for path in paths:
            if path.exists():
                return str(path)
        st.error(f"🚨 Database '{db_name}' not found!")
        return None

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    @st.cache_data
    def load_base_data(_self, origin_iata: str):
        query = """
        WITH MajorAirports AS (
            SELECT iso2, iata_code
            FROM (
                SELECT iso2, iata_code,
                       ROW_NUMBER() OVER (PARTITION BY iso2 ORDER BY passenger_volume DESC) as rank
                FROM airports
            ) WHERE rank = 1
        )
        SELECT
            c.iso2,
            c.iso3,
            c.country_name,
            c.tugo_advisory_state,

            ni.numbeo_cost_of_living_index,
            ni.numbeo_cpi_and_rent_index,
            ni.numbeo_rent_index,
            ni.numbeo_purchasing_power_incl_rent_index,
            ni.numbeo_restaurant_price_index,
            ni.numbeo_groceries_index,
            ni.numbeo_quality_of_life_index,
            ni.numbeo_health_care_index,
            ni.numbeo_pollution_index,

            c.img_1,
            c.img_2,
            c.img_3,

            cm.climate_avg_temp_c,
            (SELECT COUNT(*) FROM unesco_heritage_sites u WHERE u.country_iso = c.iso2) as unesco_count,

            fc.price_eur as flight_price,
            fc.origin as flight_origin,
            fc.destination as flight_dest

        FROM countries c
        LEFT JOIN climate_monthly cm ON c.country_name = cm.country_name_climate
        LEFT JOIN MajorAirports ma ON c.iso2 = ma.iso2
        LEFT JOIN flight_costs fc ON ma.iata_code = fc.destination AND fc.origin = ?
        LEFT JOIN numbeo_indices ni ON ni.iso3 = c.iso3
        """
        conn = _self.get_connection()
        try:
            df = pd.read_sql(query, conn, params=(origin_iata,))
        except Exception as e:
            st.error(f"🚨 SQL error in load_base_data: {e}")
            df = pd.DataFrame()
        finally:
            conn.close()
        return df

    @st.cache_data
    def get_country_details(_self, iso2: str):
        conn = _self.get_connection()
        try:
            details = {
                "safety": pd.read_sql("SELECT category, description FROM tugo_safety WHERE iso2 = ?", conn, params=(iso2,)),
                "health": pd.read_sql("SELECT disease_name, description FROM tugo_health WHERE iso2 = ? LIMIT 5", conn, params=(iso2,)),
                "entry": pd.read_sql("SELECT category, description FROM tugo_entry WHERE iso2 = ?", conn, params=(iso2,)),
                "unesco": pd.read_sql("SELECT name, category FROM unesco_heritage_sites WHERE country_iso = ? LIMIT 10", conn, params=(iso2,)),
            }
        except Exception as e:
            st.error(f"🚨 SQL error in get_country_details: {e}")
            details = {"safety": pd.DataFrame(), "health": pd.DataFrame(), "entry": pd.DataFrame(), "unesco": pd.DataFrame()}
        finally:
            conn.close()
        return details

    @st.cache_data
    def get_airports(_self, iso2=None):
        conn = sqlite3.connect(_self.db_path)
        try:
            if iso2:
                query = "SELECT iata_code, city, name FROM airports WHERE iso2 = ? ORDER BY passenger_volume DESC"
                df = pd.read_sql(query, conn, params=(iso2,))
            else:
                query = "SELECT iata_code, city, name FROM airports ORDER BY passenger_volume DESC LIMIT 500"
                df = pd.read_sql(query, conn)
        finally:
            conn.close()
        df["display"] = df["city"] + " (" + df["iata_code"] + ")"
        return df

    @st.cache_data
    def get_iata_mappings(_self):
        conn = _self.get_connection()
        try:
            df = pd.read_sql("SELECT iata_code, city, name, timezone FROM airports", conn)
        finally:
            conn.close()
        return {
            "city": df.set_index("iata_code")["city"].to_dict(),
            "name": df.set_index("iata_code")["name"].to_dict(),
            "tz": df.set_index("iata_code")["timezone"].to_dict(),
        }

    @st.cache_data
    def get_exchange_rate(_self, currency_code):
        conn = _self.get_connection()
        try:
            res = pd.read_sql(
                "SELECT one_eur_to_currency FROM numbeo_exchange_rates WHERE currency = ?",
                conn,
                params=(currency_code,),
            )
        finally:
            conn.close()
        return float(res.iloc[0]["one_eur_to_currency"]) if not res.empty else 1.0


data_manager = DataManager()

# =============================
# MATCHER
# =============================
class TravelMatcher:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def normalize(self, series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        if s.notna().sum() == 0:
            return pd.Series([0.5] * len(s), index=s.index)
        if s.nunique(dropna=True) <= 1:
            return s.fillna(s.dropna().iloc[0] if s.notna().any() else 0.5)
        return (s - s.min()) / (s.max() - s.min())

    def _stable_noise(self, key: str, seed: int) -> float:
        rnd = random.Random(f"{seed}::{key}")
        return rnd.random()

    def calculate_match(self, weights_100: dict, prefs: dict) -> pd.DataFrame:
        df = self.df.copy()

        weights_100 = normalize_weights_100(weights_100)
        weights = weights_to_unit(weights_100)

        # Safety (TuGo)
        def tugo_to_score(x):
            s = str(x)
            if "Do not travel" in s:
                return 0.1
            if "high degree" in s:
                return 0.4
            return 0.9

        df["safety_tugo_score"] = df["tugo_advisory_state"].apply(tugo_to_score)

        # Culture (UNESCO)
        unesco = pd.to_numeric(df.get("unesco_count"), errors="coerce").fillna(0)
        df["culture_score"] = self.normalize(unesco)

        # Weather fit
        target_temp = float(prefs.get("target_temp", 25))
        temp = pd.to_numeric(df.get("climate_avg_temp_c"), errors="coerce").fillna(target_temp)
        df["weather_score"] = 1 - self.normalize((temp - target_temp).abs())

        # Cost/value (lower is better)
        col = pd.to_numeric(df.get("numbeo_cost_of_living_index"), errors="coerce")
        rest = pd.to_numeric(df.get("numbeo_restaurant_price_index"), errors="coerce")
        groc = pd.to_numeric(df.get("numbeo_groceries_index"), errors="coerce")
        rent = pd.to_numeric(df.get("numbeo_rent_index"), errors="coerce")

        col_fb = safe_median(col, default=100.0)
        rest_fb = safe_median(rest, default=100.0)
        groc_fb = safe_median(groc, default=100.0)
        rent_fb = safe_median(rent, default=50.0)

        df["cost_score"] = 1 - self.normalize(col.fillna(col_fb))
        df["restaurant_value_score"] = 1 - self.normalize(rest.fillna(rest_fb))
        df["groceries_value_score"] = 1 - self.normalize(groc.fillna(groc_fb))
        df["rent_score"] = 1 - self.normalize(rent.fillna(rent_fb))

        # Luxury (high cost can be good)
        df["luxury_price_score"] = self.normalize(col.fillna(col_fb))

        # Purchasing power (higher is better)
        pp = pd.to_numeric(df.get("numbeo_purchasing_power_incl_rent_index"), errors="coerce")
        pp_fb = safe_median(pp, default=50.0)
        df["purchasing_power_score"] = self.normalize(pp.fillna(pp_fb))

        # Quality of life (higher is better)
        qol = pd.to_numeric(df.get("numbeo_quality_of_life_index"), errors="coerce")
        qol_fb = safe_median(qol, default=100.0)
        df["qol_score"] = self.normalize(qol.fillna(qol_fb))

        # Health care (higher is better)
        hc = pd.to_numeric(df.get("numbeo_health_care_index"), errors="coerce")
        hc_fb = safe_median(hc, default=50.0)
        df["health_care_score"] = self.normalize(hc.fillna(hc_fb))

        # Clean air (lower pollution is better)
        pol = pd.to_numeric(df.get("numbeo_pollution_index"), errors="coerce")
        pol_fb = safe_median(pol, default=50.0)
        df["clean_air_score"] = 1 - self.normalize(pol.fillna(pol_fb))

        # Optional spices
        if float(weights.get("astro", 0.0)) > 0:
            seed = int(prefs.get("astro_seed", 424242))
            df["astro_score"] = df["country_name"].apply(lambda c: self._stable_noise(str(c), seed))
        else:
            df["astro_score"] = 0.0

        if prefs.get("hidden_gem_mode", False):
            seed = int(prefs.get("gem_seed", 1337))
            df["hidden_gem_score"] = df["country_name"].apply(lambda c: self._stable_noise(str(c), seed))
        else:
            df["hidden_gem_score"] = 0.0

        if float(weights.get("jitter", 0.0)) > 0:
            seed = int(prefs.get("jitter_seed", 9001))
            df["jitter_score"] = df["country_name"].apply(lambda c: self._stable_noise(str(c), seed))
        else:
            df["jitter_score"] = 0.0

        # Final score in [0,1] (weights sum to 1 after conversion)
        df["final_score"] = (
            df["safety_tugo_score"] * weights.get("safety_tugo", 0.0) +
            df["cost_score"] * weights.get("cost", 0.0) +
            df["restaurant_value_score"] * weights.get("restaurant", 0.0) +
            df["groceries_value_score"] * weights.get("groceries", 0.0) +
            df["rent_score"] * weights.get("rent", 0.0) +
            df["purchasing_power_score"] * weights.get("purchasing_power", 0.0) +
            df["qol_score"] * weights.get("qol", 0.0) +
            df["health_care_score"] * weights.get("health_care", 0.0) +
            df["clean_air_score"] * weights.get("clean_air", 0.0) +
            df["culture_score"] * weights.get("culture", 0.0) +
            df["weather_score"] * weights.get("weather", 0.0) +
            df["luxury_price_score"] * weights.get("luxury_price", 0.0) +
            df["hidden_gem_score"] * weights.get("hidden_gem", 0.0) +
            df["astro_score"] * weights.get("astro", 0.0) +
            df["jitter_score"] * weights.get("jitter", 0.0)
        )

        return df.sort_values("final_score", ascending=False).reset_index(drop=True)

# =============================
# GPT FLIGHT PARAM EXTRACT
# =============================
def extract_flight_info_with_gpt(conversation_history):
    system_prompt = f"""
    You are an intelligent flight search assistant. Your goal is to extract flight search parameters
    from a user's request into a specific JSON format. Ask clarifying questions ONLY when necessary. Today's date is {datetime.date.today().strftime('%Y-%m-%d')}.

    ## JSON Output Structure:
    - Your final output MUST be a JSON object.
    - Use `originLocationCode` and `destinationLocationCode` for airport codes.
    - Use `departureDate` for single dates, or `startDate` and `endDate` for ranges. Dates must be 'YYYY-MM-DD'.
    - Use `adults`, `children`, and `infants` for traveler counts.
    - If the user wants a direct flight, include `"nonStop": true`.
    - For travel class, use `travelClass` with one of: "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST".
    - Only include the `followUpQuestion` key if information is missing.
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    try:
        completion = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=messages,
            response_format={"type": "json_object"},
        )
        response_content = completion.choices[0].message.content
        if "```json" in response_content:
            json_str = response_content.split("```json\n")[1].split("```")[0]
        else:
            json_str = response_content
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error processing your request with the AI model: {e}")
        return None


def format_duration(duration_str):
    if isinstance(duration_str, datetime.timedelta):
        total_seconds = int(duration_str.total_seconds())
        return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    match = re.match(r"PT(\d+H)?(\d+M)?", duration_str)
    h = match.group(1)[:-1] if match and match.group(1) else "0"
    m = match.group(2)[:-1] if match and match.group(2) else "0"
    return f"{h}h {m}m"


def parse_duration_to_td(duration_raw):
    match = re.match(r"PT(\d+H)?(\d+M)?", duration_raw)
    h, m = 0, 0
    if match:
        if match.group(1):
            h = int(match.group(1)[:-1])
        if match.group(2):
            m = int(match.group(2)[:-1])
    return datetime.timedelta(hours=h, minutes=m)

# =============================
# SWIPE CARDS
# =============================
SWIPE_CARDS = [
    {"id": "weather", "title": "What's the vibe?", "left": {"label": "Beach & Sun", "icon": "☀️"}, "right": {"label": "Cozy & Cool", "icon": "🧥"}},
    {"id": "budget", "title": "How are we spending?", "left": {"label": "Luxury Escape", "icon": "💎"}, "right": {"label": "Budget Adventure", "icon": "💰"}},
    {"id": "culture", "title": "What will we explore?", "left": {"label": "History & Museums", "icon": "🏛️"}, "right": {"label": "Nature & Parks", "icon": "🌳"}},
    {"id": "pace", "title": "What's the pace?", "left": {"label": "Action-Packed", "icon": "⚡"}, "right": {"label": "Relax & Unwind", "icon": "🧘"}},
    {"id": "food", "title": "Food mood?", "left": {"label": "Eat Out", "icon": "🍜"}, "right": {"label": "Cook & Chill", "icon": "🧑‍🍳"}},
    {"id": "nightlife", "title": "Night plan?", "left": {"label": "Party Mode", "icon": "🕺"}, "right": {"label": "Chill Mode", "icon": "🫖"}},
    {"id": "mobility", "title": "Move how?", "left": {"label": "Walk & Wander", "icon": "🚶"}, "right": {"label": "Hop & Go", "icon": "🚕"}},
    {"id": "hidden_gems", "title": "Mainstream or hidden gems?", "left": {"label": "Hidden Gems", "icon": "🗝️"}, "right": {"label": "Main Hits", "icon": "🎯"}},
]

# =============================
# UI STEPS
# =============================
def show_profile_step():
    st.markdown("### Step 1: 📍 Where are you starting from?")
    origin_options = {"Germany": "FRA", "United States": "ATL"}
    selected_origin = st.radio("Select origin:", list(origin_options.keys()), horizontal=True, label_visibility="collapsed")
    st.session_state.origin_iata = origin_options[selected_origin]

    st.markdown("### Step 2: 🧭 Choose Your Traveller Profile")
    st.write("Pick a profile. Advanced Customization shows weights (0–100 points) that always sum to 100.")

    personas = {
        "🗺️ Story Hunter": normalize_weights_100({
            "safety_tugo": 15, "culture": 22, "hidden_gem": 14,
            "cost": 12, "restaurant": 8, "groceries": 5,
            "weather": 10, "qol": 7, "clean_air": 5,
            "purchasing_power": 2,
            "rent": 0, "health_care": 0, "luxury_price": 0, "astro": 0, "jitter": 0
        }),
        "👨‍👩‍👧‍👦 Family Fortress": normalize_weights_100({
            "safety_tugo": 28, "health_care": 14, "qol": 12, "clean_air": 12,
            "weather": 10, "culture": 6,
            "cost": 8, "restaurant": 3, "groceries": 3,
            "purchasing_power": 4,
            "rent": 0, "hidden_gem": 0, "luxury_price": 0, "astro": 0, "jitter": 0
        }),
        "💻 WiFi Goblin (Long stay)": normalize_weights_100({
            "rent": 20, "purchasing_power": 14,
            "groceries": 10, "restaurant": 6, "cost": 12,
            "safety_tugo": 14,
            "qol": 12, "clean_air": 6,
            "weather": 4, "culture": 2,
            "hidden_gem": 0, "health_care": 0, "luxury_price": 0, "astro": 0, "jitter": 0
        }),
        "❤️ Comfort Snob": normalize_weights_100({
            "qol": 20, "safety_tugo": 18,
            "clean_air": 12, "health_care": 10,
            "weather": 10, "culture": 6,
            "luxury_price": 10, "restaurant": 4,
            "purchasing_power": 4,
            "cost": 0, "groceries": 0, "rent": 0, "hidden_gem": 2, "astro": 0, "jitter": 0
        }),
        "🧌 Budget Goblin": normalize_weights_100({
            "cost": 26, "groceries": 12, "restaurant": 10,
            "purchasing_power": 12,
            "safety_tugo": 14,
            "weather": 8, "culture": 6,
            "clean_air": 6, "qol": 4,
            "hidden_gem": 2,
            "rent": 0, "health_care": 0, "luxury_price": 0, "astro": 0, "jitter": 0
        }),
        "🌿 Clean Air & Calm": normalize_weights_100({
            "clean_air": 24, "safety_tugo": 22,
            "qol": 12, "health_care": 10, "weather": 10,
            "cost": 10, "groceries": 4, "restaurant": 2,
            "culture": 4, "hidden_gem": 2,
            "purchasing_power": 0, "rent": 0, "luxury_price": 0, "astro": 0, "jitter": 0
        }),
        "🧨 Chaos Gremlin (but not stupid)": normalize_weights_100({
            "hidden_gem": 24, "culture": 10,
            "cost": 10, "restaurant": 6, "weather": 4,
            "safety_tugo": 16, "qol": 6, "clean_air": 4,
            "purchasing_power": 4, "jitter": 10, "astro": 6,
            "luxury_price": 0, "rent": 0, "health_care": 0, "groceries": 0
        }),
    }

    persona = st.selectbox("Select a persona:", list(personas.keys()), key="persona_select", label_visibility="collapsed")
    st.session_state.persona_defaults = personas[persona].copy()

    # Persona switch: wipe slider keys BEFORE widgets are built, then write new values
    if st.session_state.get("persona_active") != persona:
        st.session_state.persona_active = persona
        for wk in WEIGHT_KEYS:
            st.session_state.pop(f"adv_{wk}", None)
        set_adv_from_weights(personas[persona])

    st.markdown("### Step 3: 📅 When is your vacation?")
    today = datetime.date.today()
    vacation_dates = st.date_input(
        "Select your travel window:",
        value=[today + datetime.timedelta(days=30), today + datetime.timedelta(days=40)],
        min_value=today,
        help="This helps us find the best flights and weather for your trip."
    )

    with st.expander("Advanced Customization (Optional)"):
        if st.button("↩ Reset to Persona Defaults", use_container_width=True):
            for wk in WEIGHT_KEYS:
                st.session_state.pop(f"adv_{wk}", None)
            set_adv_from_weights(st.session_state.persona_defaults)
            st.rerun()

        total_live = sum(clamp_int(st.session_state.get(f"adv_{k}", 0)) for k in WEIGHT_KEYS)
        st.caption(f"Current sum: **{total_live} / 100**")

        slider_row("Safety (TuGo Advisory)", "safety_tugo")
        slider_row("Cost (Cheap is good)", "cost")
        slider_row("Restaurant Value", "restaurant")
        slider_row("Groceries Value", "groceries")
        slider_row("Rent (Long stay)", "rent")
        slider_row("Purchasing Power", "purchasing_power")
        slider_row("Quality of Life", "qol")
        slider_row("Health Care", "health_care")
        slider_row("Clean Air (Low pollution)", "clean_air")
        slider_row("Culture (UNESCO)", "culture")
        slider_row("Weather Fit", "weather")
        slider_row("Luxury Price Vibe (High cost can be good)", "luxury_price")
        slider_row("Hidden Gem Spice", "hidden_gem")
        slider_row("Astro Spice", "astro")
        slider_row("Chaos Jitter", "jitter")

    if st.button("Next: Personalize Your Trip →"):
        if not (isinstance(vacation_dates, (list, tuple)) and len(vacation_dates) == 2):
            st.error("Please select both a start and end date for your vacation.")
            st.stop()

        st.session_state.start_date = vacation_dates[0]
        st.session_state.end_date = vacation_dates[1]

        committed = {k: clamp_int(st.session_state.get(f"adv_{k}", 0)) for k in WEIGHT_KEYS}
        st.session_state.weights = normalize_weights_100(committed)

        st.session_state.prefs = {
            "target_temp": 25,
            "food_style": None,
            "night_style": None,
            "move_style": None,
            "hidden_gem_mode": False,
            "gem_seed": st.session_state.get("gem_seed", random.randint(1, 10_000_000)),
            "astro_seed": st.session_state.get("astro_seed", random.randint(1, 10_000_000)),
            "jitter_seed": st.session_state.get("jitter_seed", random.randint(1, 10_000_000)),
        }

        if st.session_state.origin_iata == "ATL":
            st.session_state.currency_symbol = "$"
            st.session_state.currency_rate = data_manager.get_exchange_rate("USD")
        else:
            st.session_state.currency_symbol = "€"
            st.session_state.currency_rate = 1.0

        st.session_state.card_index = 0
        st.session_state.step = 2
        st.rerun()


def show_swiping_step():
    if st.session_state.card_index >= len(SWIPE_CARDS):
        st.session_state.step = 3
        st.rerun()
        return

    card_index = st.session_state.card_index
    progress_val = min((card_index + 1) / len(SWIPE_CARDS), 1.0)

    st.markdown(f"### Step 4: Swipe to Refine Your Choices ({card_index + 1}/{len(SWIPE_CARDS)})")
    st.progress(progress_val)

    card = SWIPE_CARDS[card_index]

    def post_update():
        st.session_state.weights = normalize_weights_100(st.session_state.weights)
        st.session_state.card_index += 1
        st.rerun()

    with st.container():
        st.markdown(f"<div class='card swipe-card'><h3>{card['title']}</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"<span class='swipe-icon'>{card['left']['icon']}</span>", unsafe_allow_html=True)
            if st.button(card["left"]["label"], key=f"left_{card_index}"):
                if card["id"] == "weather":
                    st.session_state.prefs["target_temp"] = 28
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"weather": +5})

                if card["id"] == "budget":
                    w = st.session_state.weights.copy()
                    w["luxury_price"] = max(int(w.get("luxury_price", 0)), 10)
                    w = adjust_weights_points(w, {"cost": -5})
                    st.session_state.weights = w

                if card["id"] == "culture":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"culture": +6})

                if card["id"] == "pace":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"safety_tugo": -3})

                if card["id"] == "food":
                    st.session_state.prefs["food_style"] = "eat_out"
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"restaurant": +6, "groceries": -3})

                if card["id"] == "nightlife":
                    st.session_state.prefs["night_style"] = "party"
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"culture": +3, "safety_tugo": -2})

                if card["id"] == "mobility":
                    st.session_state.prefs["move_style"] = "walk"
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"culture": +2})

                if card["id"] == "hidden_gems":
                    st.session_state.prefs["hidden_gem_mode"] = True
                    w = st.session_state.weights.copy()
                    w["hidden_gem"] = max(int(w.get("hidden_gem", 0)), 18)
                    st.session_state.weights = normalize_weights_100(w)

                post_update()

        with c2:
            st.markdown(f"<span class='swipe-icon'>{card['right']['icon']}</span>", unsafe_allow_html=True)
            if st.button(card["right"]["label"], key=f"right_{card_index}"):
                if card["id"] == "weather":
                    st.session_state.prefs["target_temp"] = 18
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"weather": +3})

                if card["id"] == "budget":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"cost": +6, "luxury_price": -4})

                if card["id"] == "culture":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"culture": -4})

                if card["id"] == "pace":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"safety_tugo": +4})

                if card["id"] == "food":
                    st.session_state.prefs["food_style"] = "cook"
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"groceries": +6, "restaurant": -3, "cost": +2})

                if card["id"] == "nightlife":
                    st.session_state.prefs["night_style"] = "chill"
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"safety_tugo": +2, "clean_air": +2})

                if card["id"] == "mobility":
                    st.session_state.weights = adjust_weights_points(st.session_state.weights, {"cost": +2})

                if card["id"] == "hidden_gems":
                    st.session_state.prefs["hidden_gem_mode"] = False
                    w = st.session_state.weights.copy()
                    w["hidden_gem"] = 0
                    st.session_state.weights = normalize_weights_100(w)

                post_update()

        st.markdown("</div>", unsafe_allow_html=True)


def show_astro_step():
    st.markdown("### Step 5: A Final Touch of Destiny? ✨")
    st.markdown("#### 🃏 Draw Your Mystical Travel Card")

    if st.button("Draw Tarot Card", use_container_width=True, key="draw_tarot"):
        try:
            api_key = os.getenv("ROXY_API_KEY")
            tarot_url = "https://roxyapi.com/api/v1/data/astro/tarot"
            url = f"{tarot_url}/single-card-draw?token={api_key}&reversed_probability=0.3"

            response = requests.get(url, timeout=20)

            if response.status_code == 200:
                card_data = response.json()
                card_name = card_data.get("name", "Unknown Card")
                is_reversed = card_data.get("is_reversed", False)
                card_image = card_data.get("image", "")

                conn = sqlite3.connect(st.session_state.get("db_path_override", "unified_country_database.db"))
                cursor = conn.cursor()

                orientation = "reversed" if is_reversed else "upright"
                cursor.execute(
                    """
                    SELECT DISTINCT country_code, country_name, reason
                    FROM tarot_countries
                    WHERE card_name = ? AND orientation = ?
                    """,
                    (card_name, orientation),
                )
                results = cursor.fetchall()
                conn.close()

                if results:
                    tarot_countries = [row[0] for row in results]
                    st.session_state["tarot_countries"] = tarot_countries

                    w = st.session_state.weights.copy()
                    w["astro"] = max(int(w.get("astro", 0)), 20)
                    st.session_state.weights = normalize_weights_100(w)

                    orientation_text = "🔄 Reversed" if is_reversed else "⬆️ Upright"
                    st.success(f"✨ **{card_name}** ({orientation_text})")

                    if card_image:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(card_image, width=200)

                    st.markdown("#### 🌍 Recommended Destinations:")
                    for country_code, country_name, reason in results:
                        st.write(f"**{country_name}** ({country_code})")
                        st.caption(f"_{reason}_")
                else:
                    st.warning(f"Card '{card_name}' found but no countries in tarot database.")
                    st.session_state["tarot_countries"] = []
            else:
                st.error(f"API Error: {response.status_code}")

        except Exception as e:
            st.error(f"Error drawing tarot card: {str(e)}")

    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    if st.button("Next: Ban List →", use_container_width=True):
        st.session_state.step = 4
        st.rerun()


def show_ban_list_step():
    st.markdown("### Step 6: 🚫 Ban List (Optional)")
    st.caption("Choose any countries you do NOT want to see. Leave empty to skip.")

    df_base = data_manager.load_base_data(st.session_state.get("origin_iata", "FRA"))
    if df_base.empty:
        st.error("No base data loaded. Check DB / query.")
        return

    iso3_to_name = (
        df_base.dropna(subset=["iso3", "country_name"])
        .drop_duplicates(subset=["iso3"])
        .set_index("iso3")["country_name"]
        .to_dict()
    )
    all_iso3 = sorted(list(iso3_to_name.keys()))

    st.multiselect(
        "Banned countries:",
        options=all_iso3,
        default=st.session_state.get("banned_iso3", []),
        format_func=lambda x: iso3_to_name.get(x, x),
        key="banned_iso3",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Skip →", use_container_width=True):
            st.session_state.step = 5
            st.rerun()
    with c2:
        if st.button("Calculate My Matches! 🚀", use_container_width=True):
            st.session_state.step = 5
            st.rerun()


def show_results_step():
    st.markdown("### Step 7: Your Top Destinations!")
    with st.spinner("Analyzing the globe to find your perfect spot..."):
        df_base = data_manager.load_base_data(st.session_state.get("origin_iata", "FRA"))

        banned_iso3 = set(st.session_state.get("banned_iso3", []))
        if banned_iso3:
            df_base = df_base[~df_base["iso3"].isin(banned_iso3)].reset_index(drop=True)

        matcher = TravelMatcher(df_base)
        st.session_state.matched_df = matcher.calculate_match(st.session_state.weights, st.session_state.prefs)

    df = st.session_state.matched_df
    if df.empty:
        st.warning("No destinations found after filters.")
        return

    top_5 = df.head(5)

    st.balloons()
    st.success(f"**Your #1 Match: {top_5.iloc[0]['country_name']}**")

    for i, row in top_5.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([1.5, 2, 1])

            with c1:
                imgs = [row.get("img_1"), row.get("img_2"), row.get("img_3")]
                imgs = [x for x in imgs if x]
                if imgs:
                    st.image(random.choice(imgs), use_container_width=True)

            with c2:
                st.markdown(f"#### {i+1}. {row['country_name']}")
                score_pct = float(row["final_score"]) * 100.0
                st.markdown(
                    f"**Match Score:** <span style='color:green; font-weight:bold'>{score_pct:.0f}%</span>",
                    unsafe_allow_html=True,
                )

                if pd.notnull(row.get("flight_price")):
                    rate = st.session_state.get("currency_rate", 1.0)
                    symbol = st.session_state.get("currency_symbol", "€")
                    converted_price = float(row["flight_price"]) * float(rate)
                    tooltip = f"Two-way flight from {row.get('flight_origin')} to {row.get('flight_dest')}"
                    st.markdown(f"✈️ Est. Flight: **{symbol}{converted_price:.0f}**", help=tooltip)

            with c3:
                if st.button("View Details", key=f"details_{row['iso2']}"):
                    st.session_state.selected_country = row
                    st.session_state.step = 6
                    st.rerun()

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()


def show_dashboard_step():
    country = st.session_state.selected_country

    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.markdown(f"### 📋 Dashboard: {country['country_name']}")
    with top_r:
        if st.button("🔁 Start Over", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛡️ Safety", "🏥 Health & Visa", "🏛️ Culture", "💰 Budget", "✈️ Find Flights"])
    details = data_manager.get_country_details(country["iso2"])

    with tab1:
        st.info(f"Advisory: {country.get('tugo_advisory_state')}")
        if not details["safety"].empty:
            st.dataframe(details["safety"], use_container_width=True)

    with tab2:
        st.write("#### Vaccinations & Diseases")
        st.dataframe(details["health"], use_container_width=True)

    with tab3:
        st.metric("UNESCO World Heritage Sites", int(country.get("unesco_count", 0) or 0))
        if not details["unesco"].empty:
            st.dataframe(details["unesco"], use_container_width=True)

    with tab4:
        st.info("Budget tab will be rebuilt: a real cost estimator based on selected Numbeo components.")
        st.metric("Numbeo Cost of Living Index (Higher = more expensive)", f"{country.get('numbeo_cost_of_living_index', float('nan'))}")

    # Flights (kept)
    with tab5:
        c_mode, c_type = st.columns([2, 1])
        mode = c_mode.radio("Search Mode", ["Manual Search", "AI Flight Chatbot"], horizontal=True)
        trip_type = c_type.selectbox("Trip Type", ["Round Trip", "One Way"])

        all_airports = data_manager.get_airports()
        dest_airports = data_manager.get_airports(country["iso2"])

        if dest_airports.empty:
            st.warning("No airports found for this country.")
            return

        if "conversation" not in st.session_state:
            st.session_state.conversation = []

        if mode == "Manual Search":
            c1, col2, col3 = st.columns(3)
            default_origin = st.session_state.get("origin_iata", "FRA")
            origin_index = (
                all_airports[all_airports["iata_code"] == default_origin].index[0]
                if not all_airports[all_airports["iata_code"] == default_origin].empty
                else 0
            )
            orig = c1.selectbox("Flying from:", all_airports["display"], index=int(origin_index))
            dest = col2.selectbox("Flying to:", dest_airports["display"])

            s_date = st.session_state.get("start_date", datetime.date.today() + datetime.timedelta(days=14))
            e_date = st.session_state.get("end_date", datetime.date.today() + datetime.timedelta(days=17))

            if trip_type == "Round Trip":
                dates = col3.date_input("Vacation Dates:", [s_date, e_date])
            else:
                dates = col3.date_input("Departure Date:", s_date)

            c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1])
            t_class = c4.selectbox("Class", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
            ad = c5.number_input("Adults (12y+)", 1, 9, 1)
            ch = c6.number_input("Children (2-11y)", 0, 9, 0)
            inf = c7.number_input("Infants (<2y)", 0, 9, 0)
            st.session_state.traveler_counts = {"ADULT": ad, "CHILD": ch, "INFANT": inf}
            non_stop = c8.checkbox("Non-stop")

            if st.button("Search Flights 🚀", use_container_width=True, key="manual_search_btn"):
                token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                all_res = {"data": [], "dictionaries": {"carriers": {}}}

                if trip_type == "Round Trip":
                    start_d = dates[0] if isinstance(dates, (list, tuple)) else dates
                    end_d = dates[0] if isinstance(dates, (list, tuple)) else dates
                else:
                    start_d = dates[0] if isinstance(dates, (list, tuple)) else dates
                    end_d = dates[1] if isinstance(dates, (list, tuple)) and len(dates) > 1 else start_d

                curr = start_d
                while curr <= end_d:
                    params = {
                        "originLocationCode": orig[-4:-1],
                        "destinationLocationCode": dest[-4:-1],
                        "departureDate": curr.strftime("%Y-%m-%d"),
                        "returnDate": dates[1].strftime("%Y-%m-%d")
                        if trip_type == "Round Trip" and isinstance(dates, (list, tuple)) and len(dates) > 1
                        else None,
                        "adults": ad,
                        "children": ch,
                        "infants": inf,
                        "travelClass": t_class,
                        "nonStop": non_stop,
                        "currencyCode": "USD" if st.session_state.origin_iata == "ATL" else "EUR",
                    }
                    res = amadeus.search_flight_offers(token, params)
                    if res and res.get("data"):
                        all_res["data"].extend(res["data"])
                        all_res["dictionaries"]["carriers"].update(res.get("dictionaries", {}).get("carriers", {}))
                    time.sleep(0.1)
                    curr += datetime.timedelta(days=1)

                st.session_state.flight_results = all_res

        else:
            st.info(
                f"Currently searching for a **{trip_type}** during your vacation: "
                f"**{st.session_state.start_date}** to **{st.session_state.end_date}**."
            )
            if prompt := st.chat_input("e.g. Find me the cheapest business class options"):
                st.session_state.conversation.append({"role": "user", "content": prompt})
                with st.spinner("AI is analyzing your request..."):
                    context_msg = {
                        "role": "system",
                        "content": f"The user is planning a {trip_type} vacation from {st.session_state.start_date} to {st.session_state.end_date}.",
                    }
                    temp_history = [context_msg] + st.session_state.conversation
                    params = extract_flight_info_with_gpt(temp_history)

                    if params and "followUpQuestion" in params:
                        st.session_state.conversation.append({"role": "assistant", "content": params["followUpQuestion"]})
                        st.rerun()

                    token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                    params = params or {}
                    params["destinationLocationCode"] = dest_airports.iloc[0]["iata_code"]
                    params["currencyCode"] = "USD" if st.session_state.origin_iata == "ATL" else "EUR"

                    if trip_type == "Round Trip":
                        params["departureDate"] = st.session_state.start_date.strftime("%Y-%m-%d")
                        params["returnDate"] = st.session_state.end_date.strftime("%Y-%m-%d")
                        start_d = end_d = st.session_state.start_date
                    else:
                        start_d = datetime.datetime.strptime(
                            params.get("departureDate") or params.get("startDate"), "%Y-%m-%d"
                        ).date()
                        end_d = datetime.datetime.strptime(
                            params.get("endDate", start_d.strftime("%Y-%m-%d")), "%Y-%m-%d"
                        ).date()

                    all_res = {"data": [], "dictionaries": {"carriers": {}}}
                    curr = start_d
                    while curr <= end_d:
                        params["departureDate"] = curr.strftime("%Y-%m-%d")
                        res = amadeus.search_flight_offers(token, params)
                        if res and res.get("data"):
                            all_res["data"].extend(res["data"])
                            all_res["dictionaries"]["carriers"].update(res.get("dictionaries", {}).get("carriers", {}))
                        time.sleep(0.1)
                        curr += datetime.timedelta(days=1)

                    st.session_state.flight_results = all_res

        if st.session_state.get("flight_results") and st.session_state.flight_results.get("data"):
            maps = data_manager.get_iata_mappings()
            carriers = st.session_state.flight_results["dictionaries"].get("carriers", {})

            processed_data = []
            for idx, offer in enumerate(st.session_state.flight_results["data"]):
                if not offer.get("itineraries"):
                    continue
                outbound = offer["itineraries"][0]
                if not outbound.get("segments"):
                    continue
                processed_data.append({
                    "idx": idx,
                    "Price": float(offer["price"]["total"]),
                    "Currency": offer["price"]["currency"],
                    "Duration": parse_duration_to_td(outbound["duration"]),
                    "Carrier": carriers.get(outbound["segments"][0]["carrierCode"], "N/A"),
                    "Layovers": len(outbound["segments"]) - 1,
                    "Departure": pd.to_datetime(outbound["segments"][0]["departure"]["at"]),
                })
            df_f = pd.DataFrame(processed_data)

            if df_f.empty:
                st.warning("No valid flight offers to display.")
                return

            with st.expander("Filters & Sorting"):
                f_col1, f_col2 = st.columns(2)
                max_p = f_col1.slider("Price", float(df_f["Price"].min()), float(df_f["Price"].max()), float(df_f["Price"].max()))
                max_dur = f_col1.slider(
                    "Duration (Hours)",
                    1,
                    int(df_f["Duration"].dt.total_seconds().max() / 3600) + 1,
                    int(df_f["Duration"].dt.total_seconds().max() / 3600) + 1,
                )
                max_lay = f_col1.slider("Layovers", 0, int(df_f["Layovers"].max()), int(df_f["Layovers"].max()))
                selected_airlines = f_col2.multiselect(
                    "Airlines",
                    options=sorted(df_f["Carrier"].unique()),
                    default=list(df_f["Carrier"].unique()),
                )
                sort_by = f_col2.selectbox("Sort by", ["Price", "Duration"])

                df_f = df_f[
                    (df_f["Price"] <= max_p) &
                    (df_f["Duration"] <= pd.to_timedelta(max_dur, unit="h")) &
                    (df_f["Layovers"] <= max_lay) &
                    (df_f["Carrier"].isin(selected_airlines))
                ].sort_values(sort_by)

            for _, row in df_f.iterrows():
                offer = st.session_state.flight_results["data"][int(row["idx"])]
                itineraries = offer.get("itineraries", [])

                with st.container(border=True):
                    for i, itin in enumerate(itineraries):
                        if i == 1:
                            st.markdown("---")

                        c1, c2 = st.columns([3, 1])
                        segs = itin.get("segments", [])
                        if not segs:
                            continue

                        with c1:
                            label = "🛫 Outbound" if len(itineraries) > 1 and i == 0 else ("🛬 Return" if i == 1 else "✈️ Flight")
                            dep_time = pd.to_datetime(segs[0]["departure"]["at"])
                            st.markdown(
                                f"**{label}** <span class='carrier-text'>{dep_time.strftime('%a, %d %b %Y')}</span>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<span class='route-text'>{carriers.get(segs[0]['carrierCode'], 'N/A')} | "
                                f"{maps['city'].get(segs[0]['departure']['iataCode'])} → "
                                f"{maps['city'].get(segs[-1]['arrival']['iataCode'])}</span>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"⏱️ {format_duration(itin['duration'])} | 🔄 {len(segs)-1} Layovers",
                                unsafe_allow_html=True,
                            )

                        if i == 0:
                            with c2:
                                curr_map = {"EUR": "€", "USD": "$"}
                                symbol = curr_map.get(row["Currency"], row["Currency"])
                                st.markdown(f"<div class='price-text'>{symbol}{row['Price']:.2f}</div>", unsafe_allow_html=True)
                                if st.button("Book Flight", key=f"bk_{int(row['idx'])}"):
                                    token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                                    price_res = amadeus.get_flight_price(token, offer)
                                    if price_res and "data" in price_res:
                                        st.session_state.priced_offer = price_res["data"]["flightOffers"][0]
                                        st.session_state.step = 7
                                        st.rerun()
                                    else:
                                        st.error("Could not confirm price.")


def show_booking_step():
    st.header("Confirm Your Booking")
    offer = st.session_state.priced_offer
    counts = st.session_state.get("traveler_counts", {"ADULT": 1, "CHILD": 0, "HELD_INFANT": 0})
    curr_map = {"EUR": "€", "USD": "$"}
    symbol = curr_map.get(offer["price"]["currency"], offer["price"]["currency"])
    st.write(f"Total Price: **{symbol}{offer['price']['total']}**")

    with st.form("traveler_form"):
        email = st.text_input("Contact Email Address")

        travelers = []
        idx = 1
        for p_type, count in counts.items():
            for _ in range(count):
                st.subheader(f"Passenger {idx} ({p_type})")
                fn, ln, dob_col = st.columns([2, 2, 2])
                f_name = fn.text_input("First Name", key=f"fn_{idx}")
                l_name = ln.text_input("Last Name", key=f"ln_{idx}")
                d_o_b = dob_col.date_input(
                    "Date of Birth",
                    value=datetime.date(1990, 1, 1),
                    key=f"dob_{idx}",
                    min_value=datetime.date(1920, 1, 1),
                    max_value=datetime.date.today(),
                )

                travelers.append({
                    "id": str(idx),
                    "dateOfBirth": d_o_b.strftime("%Y-%m-%d"),
                    "name": {"firstName": f_name.upper(), "lastName": l_name.upper()},
                    "gender": "MALE",
                    "contact": {
                        "emailAddress": email if email else "traveler@example.com",
                        "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": "123456789"}],
                    },
                })
                idx += 1

        if st.form_submit_button("Confirm & Book"):
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not email or not re.match(email_regex, email):
                st.error("🚨 Email Address is invalid")
            else:
                token = amadeus.get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
                booking_res = amadeus.create_flight_order(token, offer, travelers)

                if booking_res and "data" in booking_res:
                    st.session_state.confirmed_booking = booking_res
                    st.session_state.step = 9
                    st.rerun()
                else:
                    st.error("Booking failed. The flight may no longer be available or the connection timed out.")


def show_confirmation_step():
    if "confirmed_booking" in st.session_state:
        st.balloons()
        st.success("🎉 Booking Confirmed!")
        pnr = st.session_state.confirmed_booking["data"]["associatedRecords"][0]["reference"]
        st.subheader(f"Booking Reference (PNR): {pnr}")
    else:
        st.error("No booking record found.")

    if st.session_state.get("google_creds"):
        st.success("✅ Flight added to your Google Calendar!")

    if not st.session_state.get("google_creds") and st.button("Add to Google Calendar 📅"):
        flow = calendar_client.get_google_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
        state_payload = {"offer": st.session_state.priced_offer, "booking": st.session_state.confirmed_booking}
        state_data = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
        auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=state_data)
        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()

# =============================
# APP ROUTER
# =============================
def run_app():
    st.markdown('<div class="main-header">Your Next Adventure Awaits</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">A personalized travel planner for your individual needs.</p>', unsafe_allow_html=True)

    # session init
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "weights" not in st.session_state:
        st.session_state.weights = normalize_weights_100({
            "safety_tugo": 18,
            "cost": 12, "restaurant": 6, "groceries": 6, "rent": 0,
            "purchasing_power": 6,
            "qol": 8, "health_care": 4, "clean_air": 6,
            "culture": 10, "weather": 12,
            "luxury_price": 0,
            "astro": 0, "hidden_gem": 6, "jitter": 6
        })
    if "prefs" not in st.session_state:
        st.session_state.prefs = {
            "target_temp": 25,
            "hidden_gem_mode": False,
            "gem_seed": random.randint(1, 10_000_000),
            "astro_seed": random.randint(1, 10_000_000),
            "jitter_seed": random.randint(1, 10_000_000),
        }
    if "banned_iso3" not in st.session_state:
        st.session_state.banned_iso3 = []
    if "card_index" not in st.session_state:
        st.session_state.card_index = 0

    # routing
    if st.session_state.step == 1:
        show_profile_step()
    elif st.session_state.step == 2:
        show_swiping_step()
    elif st.session_state.step == 3:
        show_astro_step()
    elif st.session_state.step == 4:
        show_ban_list_step()
    elif st.session_state.step == 5:
        show_results_step()
    elif st.session_state.step == 6:
        show_dashboard_step()
    elif st.session_state.step == 7:
        show_booking_step()
    elif st.session_state.step == 9:
        show_confirmation_step()


if __name__ == "__main__":
    run_app()

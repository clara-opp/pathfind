import streamlit as st
from pathlib import Path
import random
import datetime
import os
import sys
import importlib
from dotenv import load_dotenv

from modules.cost_estimator import render_cost_estimator
from modules.flight_search import (
    render_flight_search,
    show_booking_step,
    show_confirmation_step,
    handle_google_oauth_callback,
)
from modules.country_overview import render_country_overview
from modules.persona_selector import render_persona_step
from modules.trip_planner import show_trip_planner
from modules.pathfind_design_light import setup_complete_design, render_pathfind_header, render_footer
from modules.auth_login_page import require_login, render_logout_button
from modules.about_page import render_about_page


# ============================================================
# CONFIG
# ============================================================
load_dotenv()
st.set_page_config(page_title="Pathfind - your personal travel planner", page_icon="✈️", layout="wide")


AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TRAVEL_BUDDY_API_KEY= os.getenv("TRAVEL_BUDDY_API_KEY")
REDIRECT_URI = "https://pathfind.streamlit.app/"

#  ============================================================
# STYLES
# ============================================================
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

        .time-badge { background-color: #1e1e1e; color: #4caf50; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-weight: 700; margin-right: 10px; border: 1px solid #4caf50; }
        .timeline-row { margin: 2px 0; display: flex; align-items: center; font-size: 0.9rem; }
        .duration-info { margin-left: 35px; color: var(--text-color); opacity: 0.6; font-style: italic; font-size: 0.8rem; }
        .layover-info { margin: 5px 0; text-align: left; padding-left: 50px; color: var(--text-color); opacity: 0.8; font-style: italic; font-size: 0.85rem; border-top: 1px dashed var(--text-color); border-bottom: 1px dashed var(--text-color); padding: 2px 0 2px 50px; }
        .city-name { font-weight: 700; color: var(--text-color); }
        .iata-code { color: var(--text-color); opacity: 0.6; }

        .swipe-question {
            text-align: center;
            font-size: 1.2rem;
            font-weight: 600;
            color: #1a237e;
            margin-bottom: 2rem;
            padding: 0 !important;
            background: none !important;
            border: none !important;
        }

        @media (max-width: 768px) {
            .stButton > button {
                height: 180px !important;
                font-size: 2.5rem !important;
            }
            .swipe-question {
                font-size: 1rem;
            }
        }

        .pride-badge-top-left {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 1.5rem;
        }

        .pride-flag-icon {
            font-size: 48px;
            cursor: pointer;
            transition: all 0.3s ease;
            filter: grayscale(1);
            padding: 0;
            border: 2px solid transparent;
            border-radius: 8px;
            line-height: 1;
        }

        .pride-flag-icon:hover {
            transform: scale(1.1);
        }

        .pride-flag-icon.active {
            filter: grayscale(0);
            border: 2px solid #FF1493;
            box-shadow: 0 0 15px rgba(255, 20, 147, 0.4);
        }

        .pride-info-btn {
            font-size: 20px;
            padding: 0;
            height: auto;
            min-height: auto;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# hardcoded region to ISO3 mapping (6 continents)
REGION_TO_ISO3 = {
    "Europe": [
        "ALB", "AND", "AUT", "BLR", "BEL", "BIH", "BGR", "HRV", "CYP", "CZE",
        "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "GIB", "HUN", "ISL", "IRL", "ITA",
        "XKX", "LVA", "LIE", "LTU", "LUX", "MLT", "MDA", "MCO", "MNE", "NLD",
        "MKD", "NOR", "POL", "PRT", "ROU", "RUS", "SMR", "SRB", "SVK", "SVN",
        "ESP", "SWE", "CHE", "UKR", "GBR", "VAT"
    ],
    "Asia": [
        "AFG", "ARM", "AZE", "BHR", "BGD", "BTN", "BRN", "KHM", "CHN", "GEO",
        "IND", "IDN", "IRN", "IRQ", "ISR", "JPN", "JOR", "KAZ", "KWT", "KGZ",
        "LAO", "LBN", "MYS", "MDV", "MNG", "MMR", "NPL", "OMN", "PAK", "PHL",
        "PSE", "QAT", "SAU", "SGP", "KOR", "LKA", "SYR", "TWN", "TJK", "THA",
        "TLS", "TKM", "TUR", "ARE", "UZB", "VNM", "YEM", "PRK"
    ],
    "Africa": [
        "DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CMR", "CPV", "CAF", "TCD",
        "COM", "COG", "COD", "CIV", "DJI", "EGY", "GNQ", "ERI", "ETH", "GAB",
        "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR", "LBY", "MDG", "MWI",
        "MLI", "MRT", "MUS", "MAR", "MOZ", "NAM", "NER", "NGA", "RWA", "STP",
        "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "SWZ", "TZA", "TGO",
        "TUN", "UGA", "ZMB", "ZWE"
    ],
    "North America": [
        "ATG", "BHS", "BRB", "BLZ", "CAN", "CRI", "CUB", "DMA", "DOM", "SLV",
        "GRD", "GTM", "HTI", "HND", "JAM", "MEX", "NIC", "PAN", "KNA", "LCA",
        "VCT", "TTO", "USA"
    ],
    "South America": [
        "ARG", "BOL", "BRA", "CHL", "COL", "ECU", "GUY", "PRY", "PER", "SUR",
        "URY", "VEN"
    ],
    "Oceania": [
        "AUS", "FJI", "KIR", "MHL", "FSM", "NRU", "NZL", "PLW", "PNG", "WSM",
        "SLB", "TON", "TUV", "VUT"
    ]
}


# ============================================================
# DYNAMIC IMPORTS
# ============================================================
def load_heavy_libs_dynamically():
    global pd, sqlite3, amadeus, calendar_client, requests, OpenAI

    pd = sys.modules.get("pandas") or importlib.import_module("pandas")
    sqlite3 = sys.modules.get("sqlite3") or importlib.import_module("sqlite3")

    openai_mod = sys.modules.get("openai") or importlib.import_module("openai")
    OpenAI = getattr(openai_mod, "OpenAI")

    amadeus = sys.modules.get("amadeus_api_client") or importlib.import_module("amadeus_api_client")
    calendar_client = sys.modules.get("google_calendar_client") or importlib.import_module("google_calendar_client")
    requests = sys.modules.get("requests") or importlib.import_module("requests")


@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

# ============================================================
# WEIGHTS / HELP
# ============================================================
WEIGHT_KEYS = [
    "safety_tugo",
    "cost", "restaurant", "groceries", "rent",
    "purchasing_power",
    "qol", "health_care", "clean_air",
    "culture", "weather",
    "luxury_price",
    "hidden_gem", "astro", "jitter",
]

# ============================================================
# SMALL HELPERS
# ============================================================
def safe_median(s, default: float) -> float:
    s = pd.to_numeric(s, errors="coerce")
    return float(s.median()) if s.notna().any() else float(default)


def clamp_int(v, lo=0, hi=100) -> int:
    try:
        v = int(round(float(v)))
    except Exception:
        v = 0
    return int(max(lo, min(hi, v)))


def normalize_weights_100(weights: dict) -> dict:
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

    total2 = sum(w_int.values())
    if total2 != 100:
        k_star = max(w_int, key=lambda kk: w_int[kk])
        w_int[k_star] = clamp_int(w_int[k_star] + (100 - total2))

    return w_int


def set_adv_from_weights(weights_100: dict):
    w = normalize_weights_100(weights_100)
    for k in WEIGHT_KEYS:
        st.session_state[f"adv_{k}"] = int(w.get(k, 0))


def _largest_remainder_allocation(shares_float: dict, total_points: int, caps: dict | None = None) -> dict:
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

        headroom = [k for k in out.keys() if out[k] < int(caps.get(k, 10**9))]
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


def weights_to_unit(weights_100: dict) -> dict:
    return {k: float(clamp_int(weights_100.get(k, 0))) / 100.0 for k in WEIGHT_KEYS}


def adjust_weights_points(weights_100: dict, deltas: dict) -> dict:
    w = {k: clamp_int(weights_100.get(k, 0)) for k in WEIGHT_KEYS}
    for k, d in deltas.items():
        if k in w:
            w[k] = clamp_int(w[k] + int(d))
    return normalize_weights_100(w)


def dedupe_one_row_per_country(df):
    if df is None or df.empty or "iso3" not in df.columns:
        return df
    df = df.dropna(subset=["iso3"]).copy()
    df["_miss"] = df.isna().sum(axis=1)
    df = (
        df.sort_values(["iso3", "_miss"])
        .drop_duplicates(subset=["iso3"], keep="first")
        .drop(columns=["_miss"])
        .reset_index(drop=True)
    )
    return df

# ============================================================
# DATA MANAGER
# ============================================================
class DataManager:
    def __init__(self, db_name="unified_country_database.db"):
        self.db_path = self._find_db(db_name)

    def _find_db(self, db_name):
        current_dir = Path(__file__).parent
        candidates = [current_dir / db_name, current_dir / "data" / db_name]
        for p in candidates:
            if p.exists():
                return str(p)
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
            fc.destination as flight_dest,

            e.equality_index_score,
            e.equality_index_legal,
            e.equality_index_public_opinion

        FROM countries c
        LEFT JOIN climate_monthly cm ON c.country_name = cm.country_name_climate
        LEFT JOIN MajorAirports ma ON c.iso2 = ma.iso2
        LEFT JOIN flight_costs fc ON ma.iata_code = fc.destination AND fc.origin = ?
        LEFT JOIN numbeo_indices ni ON ni.iso3 = c.iso3
        LEFT JOIN equality_index e ON e.iso3 = c.iso3
        """
        conn = _self.get_connection()
        try:
            df = pd.read_sql(query, conn, params=(origin_iata,))

            # Fallback image: High-quality "View from Airplane Window" (works for any destination)
            # Fills missing images so the Results Page and Slideshow never show blanks.
            fallback_img = "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2074&auto=format&fit=crop"
            if not df.empty and "img_1" in df.columns:
                df["img_1"] = df["img_1"].fillna(fallback_img)
                df.loc[df["img_1"].astype(str).str.strip() == "", "img_1"] = fallback_img

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
                "tugo_safety": pd.read_sql("SELECT category, description FROM tugo_safety WHERE iso2 = ?", conn, params=(iso2,)),
                "tugo_health": pd.read_sql("SELECT disease_name, description FROM tugo_health WHERE iso2 = ? LIMIT 10", conn, params=(iso2,)),
                "tugo_laws": pd.read_sql("SELECT category, description FROM tugo_laws WHERE iso2 = ?", conn, params=(iso2,)),
                "tugo_entry": pd.read_sql("SELECT category, description FROM tugo_entry WHERE iso2 = ?", conn, params=(iso2,)),
                "unesco": pd.read_sql("SELECT name, category FROM unesco_heritage_sites WHERE country_iso = ? LIMIT 10", conn, params=(iso2,)),
            }
        except Exception as e:
            st.error(f"🚨 SQL error in get_country_details: {e}")
            details = {
                "tugo_safety": pd.DataFrame(), 
                "tugo_health": pd.DataFrame(), 
                "tugo_laws": pd.DataFrame(), 
                "tugo_entry": pd.DataFrame(), 
                "unesco": pd.DataFrame()
            }
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
                query = "SELECT iata_code, city, name FROM airports ORDER BY passenger_volume DESC LIMIT 1000"
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

# ============================================================
# MATCHER
# ============================================================
class TravelMatcher:
    def __init__(self, df):
        self.df = df.copy()

    def _winsorize(self, s, lower_q=0.05, upper_q=0.95):
        s = pd.to_numeric(s, errors="coerce")
        if s.notna().sum() < 3:
            return s
        lo = float(s.quantile(lower_q))
        hi = float(s.quantile(upper_q))
        if lo > hi:
            lo, hi = hi, lo
        return s.clip(lower=lo, upper=hi)

    def normalize(self, series):
        s = pd.to_numeric(series, errors="coerce")

        if s.notna().sum() == 0:
            return pd.Series([0.5] * len(s), index=s.index)

        s = self._winsorize(s, 0.05, 0.95)

        if s.nunique(dropna=True) <= 1:
            fill_val = s.dropna().iloc[0] if s.notna().any() else 0.5
            return s.fillna(fill_val)

        mn = float(s.min(skipna=True))
        mx = float(s.max(skipna=True))
        if mx - mn == 0:
            return pd.Series([0.5] * len(s), index=s.index)

        return (s - mn) / (mx - mn)

    def _stable_noise(self, key: str, seed: int) -> float:
        rnd = random.Random(f"{seed}::{key}")
        return rnd.random()

    def calculate_match(self, weights_100: dict, prefs: dict):
        df = self.df.copy()
        weights_100 = normalize_weights_100(weights_100)
        weights = weights_to_unit(weights_100)
        
        def tugo_to_score(x):
            if pd.isna(x):
                return 0.5
            s = str(x)
            if "Do not travel" in s:
                return 0.1
            if "high degree" in s:
                return 0.4
            return 0.9

        df["safety_tugo_score"] = df["tugo_advisory_state"].apply(tugo_to_score)

        unesco = pd.to_numeric(df.get("unesco_count"), errors="coerce").fillna(0)
        df["culture_score"] = self.normalize(unesco)

        target_temp = float(prefs.get("target_temp", 25))
        temp_raw = pd.to_numeric(df.get("climate_avg_temp_c"), errors="coerce")
        miss_temp = temp_raw.isna()
        temp_filled = temp_raw.fillna(target_temp)
        weather_score = 1 - self.normalize((temp_filled - target_temp).abs())
        weather_score = pd.to_numeric(weather_score, errors="coerce").fillna(0.5)
        weather_score.loc[miss_temp] = 0.5
        df["weather_score"] = weather_score

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
        df["luxury_price_score"] = self.normalize(col.fillna(col_fb))

        pp = pd.to_numeric(df.get("numbeo_purchasing_power_incl_rent_index"), errors="coerce")
        pp_fb = safe_median(pp, default=50.0)
        df["purchasing_power_score"] = self.normalize(pp.fillna(pp_fb))

        qol = pd.to_numeric(df.get("numbeo_quality_of_life_index"), errors="coerce")
        qol_fb = safe_median(qol, default=100.0)
        df["qol_score"] = self.normalize(qol.fillna(qol_fb))

        hc = pd.to_numeric(df.get("numbeo_health_care_index"), errors="coerce")
        hc_fb = safe_median(hc, default=50.0)
        df["health_care_score"] = self.normalize(hc.fillna(hc_fb))

        pol = pd.to_numeric(df.get("numbeo_pollution_index"), errors="coerce")
        pol_fb = safe_median(pol, default=50.0)
        df["clean_air_score"] = 1 - self.normalize(pol.fillna(pol_fb))

        gem_seed = int(prefs.get("gem_seed", 1337))
        low_unesco_score = 1 - self.normalize(unesco)
        noise_score = df["country_name"].apply(lambda c: self._stable_noise(str(c), gem_seed))

        df["hidden_gem_score"] = (
            0.80 * (low_unesco_score ** 2.0) +
            0.20 * noise_score
        )

        # Tarot countries boost (varying per country)
        tarot_countries = st.session_state.get("tarot_countries", [])
        if tarot_countries and float(weights.get("astro", 0.0)) > 0:
            mask = df["iso2"].isin(tarot_countries)

            astro_seed = int(prefs.get("astro_seed", 4242))

            # stable but run-dependent variation per country
            noise = df["iso2"].apply(
                lambda x: self._stable_noise(str(x), astro_seed)
            )

            # Tarot countries get strong but varying astro score
            # range: 0.80 – 1.00
            df["astro_score"] = 0.0
            df.loc[mask, "astro_score"] = 0.80 + 0.20 * noise[mask]
        else:
            df["astro_score"] = 0.0


        if float(weights.get("jitter", 0.0)) > 0:
            seed = int(prefs.get("jitter_seed", 9001))
            df["jitter_score"] = df["country_name"].apply(lambda c: self._stable_noise(str(c), seed))
        else:
            df["jitter_score"] = 0.0

        df["final_score_raw"] = (
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
        
        raw = pd.to_numeric(df["final_score_raw"], errors="coerce").fillna(0.0)
        df["final_score"] = raw.clip(lower=0.0, upper=1.0)

        return df.sort_values("final_score", ascending=False).reset_index(drop=True)

# ============================================================
# SWIPE CARDS
# ============================================================
SWIPE_CARDS_ALL = [
    {"id": "weather", "title": "What's the vibe?", "left": {"label": "Beach & Sun", "icon": "☀️"}, "right": {"label": "Cozy & Cool", "icon": "🧥"}},
    {"id": "budget", "title": "How are we spending?", "left": {"label": "Luxury Escape", "icon": "💎"}, "right": {"label": "Budget Adventure", "icon": "💰"}},
    {"id": "culture", "title": "What will we explore?", "left": {"label": "History & Museums", "icon": "🏛️"}, "right": {"label": "Nature & Parks", "icon": "🌳"}},
    {"id": "pace", "title": "What's the pace?", "left": {"label": "Action-Packed", "icon": "⚡"}, "right": {"label": "Relax & Unwind", "icon": "🧘"}},
    {"id": "food", "title": "Food mood?", "left": {"label": "Eat Out", "icon": "🍜"}, "right": {"label": "Cook & Chill", "icon": "🧑‍🍳"}},
    {"id": "nightlife", "title": "Night plan?", "left": {"label": "Party Mode", "icon": "🕺"}, "right": {"label": "Chill Mode", "icon": "🫖"}},
    {"id": "mobility", "title": "Move how?", "left": {"label": "Walk & Wander", "icon": "🚶"}, "right": {"label": "Hop & Go", "icon": "🚕"}},
    {"id": "hidden_gems", "title": "Mainstream or hidden gems?", "left": {"label": "Hidden Gems", "icon": "🗝️"}, "right": {"label": "Main Hits", "icon": "🎯"}},
    {"id": "air", "title": "Breathe mode or city chaos?", "left": {"label": "Air Lungs", "icon": "🌲"}, "right": {"label": "I can handle smog", "icon": "🏙️"}},
    {"id": "hospital", "title": "Health insurance arc unlocked?", "left": {"label": "I’m a fragile legend", "icon": "🏥"}, "right": {"label": "I respawn at 100%", "icon": "😤"}},
    {"id": "long_stay", "title": "Suitcase home base or hop-scotch?", "left": {"label": "Settle in", "icon": "🧳"}, "right": {"label": "Hop around", "icon": "✈️"}},
]

# ============================================================
# SESSION INIT
# ============================================================
def init_session_state():
    st.session_state.setdefault("step", 1)
    # define a default human
    st.session_state.setdefault(
        "weights",
        normalize_weights_100({
            "safety_tugo": 10,
            "cost": 10, "restaurant": 5, "groceries": 5, "rent": 0,
            "purchasing_power": 5,
            "qol": 10, "health_care": 5, "clean_air": 5,
            "culture": 10, "weather": 10,
            "luxury_price": 5,
            "astro": 0, "hidden_gem": 10, "jitter": 10
        })
    )

    st.session_state.setdefault(
        "prefs",
        {
            "target_temp": 25,
            "gem_seed": random.randint(1, 10_000_000),
            "astro_seed": random.randint(1, 10_000_000),
            "jitter_seed": random.randint(1, 10_000_000),
        }
    )

    st.session_state.setdefault("banned_iso3", [])
    st.session_state.setdefault("card_index", 0)

    st.session_state.setdefault("tarot_drawn", False)
    st.session_state.setdefault("tarot_countries", [])
    st.session_state.setdefault("tarot_card", {})
    st.session_state.setdefault("tarot_travel_meaning", "")
    st.session_state.setdefault("tarot_travel_style", "")


    st.session_state.setdefault("lgbtq_filter_active", False)

    st.session_state.setdefault("swipe_mode_chosen", False)
    st.session_state.setdefault("active_swipe_cards", [])

    st.session_state.setdefault("ban_mode", None)

# ============================================================
# UI STEPS
# ============================================================
def show_basic_info_step(data_manager):
    """Step 1: Nationality, LGBTQ filter, and vacation dates"""
    
    st.markdown("### What is your nationality?")
    
    # Direktes Query der Datenbank für alle Länder
    conn = data_manager.get_connection()
    try:
        countries_df = pd.read_sql(
            "SELECT DISTINCT iso2, iso3, country_name FROM countries ORDER BY country_name ASC",
            conn
        )
    except Exception as e:
        st.error(f"Error loading countries: {e}")
        countries_df = pd.DataFrame()
    finally:
        conn.close()
    
    if countries_df.empty:
        st.error("Could not load countries from database")
        return
    
    # Create selectbox with country names
    country_names = countries_df["country_name"].tolist()
    
    # Set default index to Germany if available
    default_idx = 0
    if "Germany" in country_names:
        default_idx = country_names.index("Germany")
    
    # Nationality + LGBTQ button in einer Reihe
    col_nationality, col_lgbtq = st.columns([0.88, 0.12], vertical_alignment="bottom")
    
    with col_nationality:
        selected_nationality_name = st.selectbox(
            "Select country of nationality",
            options=country_names,
            index=default_idx,
            key="passport_nationality_select",
            help="This helps us show visa requirements for your destination"
        )
    
    with col_lgbtq:
        c_flag, c_info = st.columns([0.65, 0.35], vertical_alignment="bottom")
        with c_flag:
            if "lgbtq_filter_active" not in st.session_state:
                st.session_state.lgbtq_filter_active = False
            
            is_active = st.session_state.lgbtq_filter_active
            
            if st.button(
                f"{'🏳️‍🌈' if is_active else '🏳️'}",
                key="lgbtq_toggle",
                help="LGBTQ+ Safe Travel Filter",
                use_container_width=True
            ):
                st.session_state.lgbtq_filter_active = not st.session_state.lgbtq_filter_active
                st.rerun()
        with c_info:
            with st.popover("ⓘ", use_container_width=True):
                st.markdown("""
                **LGBTQ+ Safe Travel**
                
                Filters for countries with stronger legal protections and societal acceptance.
                
                *Note: Data-based guidance only. Not a guarantee of individual safety.*
                """)
    
    # Get ISO codes for selected nationality and set defaults
    if selected_nationality_name:
        selected_row = countries_df[countries_df["country_name"] == selected_nationality_name]
        if not selected_row.empty:
            passport_iso2 = selected_row.iloc[0]["iso2"]
            passport_iso3 = selected_row.iloc[0]["iso3"]
            st.session_state['passport_iso2'] = passport_iso2
            st.session_state['passport_iso3'] = passport_iso3
            st.session_state['nationality_name'] = selected_nationality_name
            
            # Set airport and currency based on nationality
            origin_country_map = {"Germany": ("FRA", "€"), "United States": ("ATL", "$")}
            
            if selected_nationality_name in origin_country_map:
                iata_code, currency = origin_country_map[selected_nationality_name]
                st.session_state["origin_iata"] = iata_code
                
                # Set currency based on nationality
                if currency == "$":
                    st.session_state.currency_symbol = "$"
                    st.session_state.currency_rate = data_manager.get_exchange_rate("USD")
                else:
                    st.session_state.currency_symbol = "€"
                    st.session_state.currency_rate = 1.0
            else:
                # Default to Germany/EUR for other countries
                st.session_state["origin_iata"] = "FRA"
                st.session_state.currency_symbol = "€"
                st.session_state.currency_rate = 1.0
    
    st.markdown("---")
    
    # Vacation dates
    st.markdown("### When is your vacation?")
    today = datetime.date.today()
    vacation_dates = st.date_input(
        "Select your travel window",
        value=(today + datetime.timedelta(days=30), today + datetime.timedelta(days=40)),
        min_value=today,
        help="This helps us find the best flights and weather for your trip.",
    )
    
    # Next button
    if st.button("Next: Choose Your Profile"):
        if not isinstance(vacation_dates, (list, tuple)) or len(vacation_dates) != 2:
            st.error("Please select both a start and end date for your vacation.")
            st.stop()
        
        st.session_state.start_date = vacation_dates[0]
        st.session_state.end_date = vacation_dates[1]
        


        # NEW RUN = NEW SEEDS
        st.session_state.prefs["gem_seed"] = random.randint(1, 10_000_000)
        st.session_state.prefs["astro_seed"] = random.randint(1, 10_000_000)
        st.session_state.prefs["jitter_seed"] = random.randint(1, 10_000_000)
        st.session_state.swipe_mode_chosen = False
        st.session_state.active_swipe_cards = []
        st.session_state.card_index = 0
        # allow drawing a new tarot card
        st.session_state["tarot_drawn"] = False
        st.session_state["tarot_countries"] = []
        st.session_state["tarot_card"] = {}
        st.session_state["tarot_travel_meaning"] = ""
        st.session_state["tarot_travel_style"] = ""

        st.session_state.step = 2
        st.rerun()


def _choose_swipe_cards(mode: str):
    all_cards = list(SWIPE_CARDS_ALL)
    seed = int(st.session_state.prefs.get("jitter_seed", random.randint(1, 10_000_000)))
    rnd = random.Random(seed)
    return rnd.sample(all_cards, k=min(6, len(all_cards)))


def show_swiping_step():
    if not st.session_state.get("swipe_mode_chosen", False):
        st.session_state.active_swipe_cards = _choose_swipe_cards("random")
        st.session_state.card_index = 0
        st.session_state.swipe_mode_chosen = True
        st.rerun()
        return

    cards = st.session_state.get("active_swipe_cards") or list(SWIPE_CARDS_ALL)
    if st.session_state.card_index >= len(cards):
        st.session_state.step = 4
        st.rerun()
        return

    idx = st.session_state.card_index
    st.markdown("### Swipe to Refine Your Choices")
    st.progress(min((idx + 1) / len(cards), 1.0))

    card = cards[idx]

    SWIPE_STRENGTH = 1.5   # change for different strength level

    def _scale_deltas(deltas: dict, factor: float) -> dict:
        out = {}
        for k, v in deltas.items():
            if k in WEIGHT_KEYS:
                out[k] = int(round(float(v) * factor))
            else:
                out[k] = v
        return out

    def apply_tradeoff(deltas: dict, prefs_update: dict | None = None):
        if prefs_update:
            st.session_state.prefs.update(prefs_update)
        st.session_state.weights = adjust_weights_points(
            st.session_state.weights,
            _scale_deltas(deltas, SWIPE_STRENGTH)
        )

    def post_update():
        st.session_state.weights = normalize_weights_100(st.session_state.weights)
        st.session_state.card_index += 1
        st.rerun()

    st.markdown(f"<div class='swipe-question'>{card['title']}</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="swipe-card-container">', unsafe_allow_html=True)

    TRADEOFFS = {
        "weather": {
            "left":  ({"weather": +15, "culture": -7, "cost": -7}, {"target_temp": 28}),
            "right": ({"weather": +12, "culture": +5, "cost": -7}, {"target_temp": 18}),
        },
        "budget": {
            "left":  ({"luxury_price": +18, "cost": -10, "rent": -6}, None),
            "right": ({"cost": +18, "luxury_price": -10, "restaurant": -6}, None),
        },
        "culture": {
            "left":  ({"culture": +16, "jitter": -8, "clean_air": -6}, None),
            "right": ({"clean_air": +16, "culture": -8, "restaurant": -6}, None),
        },
        "pace": {
            "left":  ({"jitter": +14, "safety_tugo": -8, "qol": -6}, None),
            "right": ({"qol": +14, "jitter": -8, "safety_tugo": +6}, None),
        },
        "food": {
            "left":  ({"restaurant": +15, "groceries": -8, "cost": -5}, {"food_style": "eat_out"}),
            "right": ({"groceries": +15, "restaurant": -8, "cost": +5}, {"food_style": "cook"}),
        },
        "nightlife": {
            "left":  ({"culture": +12, "restaurant": +8, "safety_tugo": -7}, {"night_style": "party"}),
            "right": ({"safety_tugo": +12, "clean_air": +8, "restaurant": -7}, {"night_style": "chill"}),
        },
        "mobility": {
            "left":  ({"culture": +12, "cost": -8, "jitter": -6}, {"move_style": "walk"}),
            "right": ({"cost": +12, "culture": -8, "jitter": +6}, {"move_style": "hop"}),
        },
        "hidden_gems": {
            "left":  ({"hidden_gem": +30, "culture": -10, "safety_tugo": -6}, None),
            "right": ({"hidden_gem": -25, "culture": +10, "qol": +6}, None),
        },
        "air": {
            "left":  ({"clean_air": +16, "qol": +8, "culture": -8}, None),
            "right": ({"culture": +10, "restaurant": +8, "clean_air": -8}, None),
        },
        "hospital": {
            "left":  ({"health_care": +16, "safety_tugo": +8, "jitter": -8}, None),
            "right": ({"health_care": -10, "hidden_gem": +12, "jitter": +6}, None),
        },
        "long_stay": {
            "left":  ({"rent": +16, "groceries": +8, "jitter": -8}, None),
            "right": ({"jitter": +6, "culture": +12, "rent": -10}, None),
        },
    }

    c1, c2 = st.columns(2, gap="medium")

    with c1:
        if st.button(f"{card['left']['icon']}\n{card['left']['label']}", key=f"left_{idx}", use_container_width=True):
            spec = TRADEOFFS.get(card["id"], {}).get("left")
            if spec:
                deltas, prefs_update = spec
                apply_tradeoff(deltas, prefs_update)
            post_update()

    with c2:
        if st.button(f"{card['right']['icon']}\n{card['right']['label']}", key=f"right_{idx}", use_container_width=True):
            spec = TRADEOFFS.get(card["id"], {}).get("right")
            if spec:
                deltas, prefs_update = spec
                apply_tradeoff(deltas, prefs_update)
            post_update()
    st.markdown('</div>', unsafe_allow_html=True) 


def show_astro_step(data_manager):
    st.markdown(
        """
        <style>
        .astro-container {
            background: linear-gradient(135deg, #0c0c1a 0%, #1a0033 50%, #330066 100%);
            padding: 2rem;
            border-radius: 20px;
            color: #e6d9ff;
            text-align: center;
            box-shadow: 0 0 30px rgba(138, 43, 226, 0.5);
            margin: 1rem 0;
            font-family: 'Georgia', serif;
        }
        .card-title {
            font-size: 2.5rem;
            background: linear-gradient(45deg, #ffd700, #ffed4e, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.8);
            margin-bottom: 1rem;
        }
        .meaning-box {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 15px;
            padding: 1rem;
            margin: 0.8rem 0;
            font-size: 0.95rem;
            line-height: 1.4;
        }
        .meaning-box h4 {
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
        }
        .meaning-box p {
            margin: 0;
        }
        .stars {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            background: radial-gradient(2px 2px at 20px 30px, #eee, transparent),
                        radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
                        radial-gradient(1px 1px at 90px 40px, #fff, transparent),
                        radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
            animation: sparkle 3s infinite;
        }
        @keyframes sparkle {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
        </style>
        <div style="position: relative;">
            <div class="stars"></div>
            <div class="astro-container">
                <div class="card-title">✨ A Final Touch of Destiny? ✨</div>
                <p style="font-size: 1.2rem; margin-bottom: 0;">Draw from the cosmic deck or trust pure logic?</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.tarot_drawn:
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            if st.button("🃏 Draw travel tarot card", key="draw_tarot", use_container_width=True):
                try:
                    api_key = os.getenv("ROXY_API_KEY")
                    tarot_url = "https://roxyapi.com/api/v1/data/astro/tarot"
                    url = f"{tarot_url}/single-card-draw?token={api_key}&reversed_probability=0.3"
                    response = requests.get(url, timeout=20)

                    if response.status_code != 200:
                        st.error(f"Cosmic connection failed: {response.status_code}")
                        return

                    card_data = response.json()
                    card_name = card_data.get("name", "Unknown Card")
                    is_reversed = bool(card_data.get("is_reversed", False))
                    orientation = "reversed" if is_reversed else "upright"

                    # ✅ FETCH FROM DATABASE: country_code, travel_meaning, travel_style
                    conn = data_manager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT DISTINCT country_code, travel_meaning, travel_style
                        FROM tarot_countries
                        WHERE card_name = ? AND orientation = ?
                        """,
                        (card_name, orientation),
                    )
                    results = cursor.fetchall()
                    conn.close()

                    # Extract countries + DB data
                    tarot_countries = [row[0] for row in results]  # List of country_code
                    
                    # Get FIRST row for travel_meaning and travel_style
                    travel_meaning = results[0][1] if results else "Destiny guides your path..."
                    travel_style = results[0][2] if results else ""

                    # Save to session state
                    st.session_state["tarot_countries"] = tarot_countries  # Countries for score boost
                    st.session_state.tarot_card = card_data  # API data
                    st.session_state["tarot_travel_meaning"] = travel_meaning
                    st.session_state["tarot_travel_style"] = travel_style

                    # Apply astro boost ()
                    w = st.session_state.weights.copy()
                    w["astro"] = 33
                    st.session_state.weights = normalize_weights_100(w)

                    st.session_state.tarot_drawn = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Stars misaligned: {str(e)}")

        with col2:
            if st.button("Skip, let's keep it rational →", key="skip_tarot", use_container_width=True):
                w = st.session_state.weights.copy()
                w["astro"] = 0
                st.session_state.weights = normalize_weights_100(w)
                st.session_state["tarot_drawn"] = False
                st.session_state["tarot_countries"] = []
                st.session_state["tarot_card"] = {}
                st.session_state["tarot_travel_meaning"] = ""
                st.session_state.step = 5
                st.rerun()

    # DISPLAY (after draw)
    if st.session_state.tarot_drawn:
        card_data = st.session_state.get("tarot_card", {})
        card_name = card_data.get("name", "Unknown Card")
        is_reversed = bool(card_data.get("is_reversed", False))
        card_image = card_data.get("image", "")
        orientation_emoji = "🔄" if is_reversed else "⬆️"

        # 3 Meanings
        general_meaning = card_data.get("meaning", "Cosmic wisdom awaits...")
        travel_meaning = st.session_state.get("tarot_travel_meaning", "Destiny guides your path...")
        travel_style = st.session_state.get("tarot_travel_style", "")

        st.markdown(
            f"""
            <div class="astro-container" style="padding: 1.5rem; margin-top: 2rem;">
                <div class="card-title">{orientation_emoji} {card_name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_img, col_text = st.columns([1, 1.5], gap="large")

        with col_img:
            if card_image:
                st.image(card_image, width=280)

        with col_text:
            # 1.General Meaning (from API)
            st.markdown(
                f"""
                <div class="meaning-box">
                    <h4>🌌 General Meaning</h4>
                    <p>{general_meaning}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 2.Travel Meaning (from Database)
            st.markdown(
                f"""
                <div class="meaning-box">
                    <h4>✈️ Travel Meaning</h4>
                    <p>{travel_meaning}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 3.Travel Style (from Database, only if present)
            if travel_style:
                st.markdown(
                    f"""
                    <div class="meaning-box">
                        <h4>🎯 Travel Style</h4>
                        <p>{travel_style}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        if st.button("➡️ Next: Ban List", use_container_width=True, key="next_tarot"):
            st.session_state.step = 5
            st.rerun()

def show_ban_choices_step(datamanager):
    st.markdown("### 🚫 Ban List (Optional)")
    st.caption("Do you want to exclude specific regions from your recommendations?")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ban a region", use_container_width=True, key="ban_choice_yes"):
            st.session_state["ban_mode"] = "use"
            st.session_state.step = 5.1
            st.rerun()
    with c2:
        if st.button("Skip, show me my matches →", use_container_width=True, key="ban_choice_skip"):
            st.session_state["ban_mode"] = "skip"
            st.session_state.step = 6
            st.rerun()


def show_ban_list_step(data_manager):
    st.markdown("### 🚫 Ban List (Optional)")
    st.caption(
        "Quickly exclude whole regions from your recommendations. "
        "Leave everything unselected to keep the whole world in play."
    )

    region_to_iso3 = REGION_TO_ISO3.copy()
    bannedregions = set(st.session_state.get("bannedregions", set()))

    nice_order = ["Europe", "Asia", "North America", "South America", "Africa", "Oceania"]
    regions = [r for r in nice_order if r in region_to_iso3] + [r for r in region_to_iso3.keys() if r not in nice_order]

    st.markdown("#### Pick regions you want to exclude")
    st.caption("Tap one or more regions below. We will hide all countries from those areas in your results.")

    cols = st.columns(3)
    for idx, region in enumerate(regions):
        col = cols[idx % 3]
        is_banned = region in bannedregions
        label = f"❌ {region}" if is_banned else region
        button_key = f"ban_region_{region}"

        with col:
            clicked = st.button(
                label,
                use_container_width=True,
                key=button_key,
                type="primary" if is_banned else "secondary"
            )
            if clicked:
                if is_banned:
                    bannedregions.discard(region)
                else:
                    bannedregions.add(region)
                st.session_state["bannedregions"] = bannedregions
                st.rerun()

    bannediso3 = set()
    for region in bannedregions:
        bannediso3.update(region_to_iso3.get(region, []))

    st.session_state["bannediso3"] = sorted(bannediso3)

    if bannedregions:
        st.markdown(f"**You are currently excluding:** {', '.join(f'🚫 {r}' for r in sorted(bannedregions))}")
    else:
        st.caption("No regions excluded. Your matches can come from anywhere! 🌍")

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Calculate My Matches! 🎯", use_container_width=True, key="ban_regions_calc"):
            st.session_state.step = 6
            st.rerun()


def show_results_step(data_manager):
    """Show results with Start Over button TOP RIGHT ONLY (no emoji, no back)"""
    
    # Include back and restart
    nav_col_left, nav_spacer, nav_col_right = st.columns([0.18, 0.64, 0.18])

    with nav_col_left:
        if st.button(
            "Back to Ban List",
            key="results_back_to_banlist",
            use_container_width=True,
            help="Adjust banned regions and recalculate matches"
        ):
            # No reset, just back to ban
            st.session_state.step = 5.1 
            st.rerun()

    with nav_col_right:
        if st.button(
            "Start Over",
            key="results_start_over",
            use_container_width=True,
            help="Reset and begin again"
        ):
            st.session_state.step = 1
            st.rerun()
    
    # Main content
    st.markdown("### Your Top Destinations!")
    st.caption("Based on your preferences and filters, here are your personalized matches.")

    with st.spinner("Analyzing the globe to find your perfect spot..."):
        dfbase = data_manager.load_base_data(st.session_state.get("origin_iata", "FRA"))
        if dfbase.empty:
            st.error("No base data loaded. Check DB query.")
            return

        if st.session_state.get("lgbtq_filter_active", False):
            if "equality_index_score" in dfbase.columns:
                dfbase = dfbase[dfbase["equality_index_score"] >= 60].reset_index(drop=True)
                st.info("🏳️‍🌈 Filtered to LGBTQ+ friendly destinations")
            else:
                st.warning("Equality Index data not available in database")

        bannediso3 = set(st.session_state.get("bannediso3", []))

        all_continents = {"Europe", "Asia", "Africa", "North America", "South America", "Oceania"}
        banned_regions = st.session_state.get("bannedregions", set())
        all_continents_banned = len(banned_regions) == 6 and banned_regions == all_continents

        if bannediso3 and "iso3" in dfbase.columns:
            beforecount = len(dfbase)
            dfbase = dfbase[~dfbase["iso3"].isin(bannediso3)].reset_index(drop=True)
            aftercount = len(dfbase)
            if beforecount - aftercount > 0:
                st.info(f"🚫 Filtered out {beforecount - aftercount} destinations from banned regions.")

        if all_continents_banned:
            st.info("🏝️ We do not have any travel destinations outside of this earth, but maybe you like one of the following islands. If you want to skip the algorithm entirely, just select your country of choice here.")
            
            # Load all countries from database
            conn = data_manager.get_connection()
            try:
                all_countries_df = pd.read_sql(
                    "SELECT DISTINCT iso2, iso3, country_name FROM countries ORDER BY country_name ASC",
                    conn
                )
            except Exception as e:
                st.error(f"Error loading countries: {e}")
                all_countries_df = pd.DataFrame()
            finally:
                conn.close()
            
            if not all_countries_df.empty:
                col_dropdown, col_button = st.columns([3, 1])
                
                with col_dropdown:
                    country_names = all_countries_df["country_name"].tolist()
                    selected_country_name = st.selectbox(
                        "Select a country",
                        options=[""] + country_names,
                        key="direct_country_select",
                        label_visibility="collapsed"
                    )
                
                with col_button:
                    if selected_country_name and selected_country_name != "":
                        if st.button("Go to Country", use_container_width=True, key="go_to_direct_country"):
                            selected_row = all_countries_df[all_countries_df["country_name"] == selected_country_name]
                            if not selected_row.empty:
                                iso2 = selected_row.iloc[0]["iso2"]
                                
                                df_base_full = data_manager.load_base_data(st.session_state.get("origin_iata", "FRA"))
                                country_data = df_base_full[df_base_full["iso2"] == iso2]
                                if not country_data.empty:
                                    st.session_state["selected_country"] = country_data.iloc[0].to_dict()
                                    st.session_state["is_direct_selection"] = True  # ← ADD THIS FLAG
                                    st.session_state.step = 7
                                    st.rerun()
                                else:
                                    st.error(f"Could not load data for {selected_country_name}")
            
            st.markdown("---")

        dfbase = dedupe_one_row_per_country(dfbase)
        matcher = TravelMatcher(dfbase)
        st.session_state["matcheddf"] = matcher.calculate_match(st.session_state.weights, st.session_state.prefs)
        df = st.session_state["matcheddf"]

        if df.empty:
            st.warning("No destinations found after filters.")
            return

        top3 = df.head(3)
        st.balloons()
        st.success(f"🎉 Your #1 Match: {top3.iloc[0]['country_name']}")

        for i, row in top3.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1.5, 2, 1])
                with c1:
                    imgs = [row.get("img_1"), row.get("img_2"), row.get("img_3")]
                    imgs = [x for x in imgs if x]
                    if imgs:
                        st.image(random.choice(imgs), use_container_width=True)
                with c2:
                    st.markdown(f"**{i+1}. {row['country_name']}**")
                    score_pct = float(row.get("final_score", 0.0)) * 100.0
                    a, b = st.columns([0.88, 0.12], vertical_alignment="center")
                    with a:
                        st.markdown(
                            f"Match Score: <span style='color:green; font-weight:bold'>{score_pct:.0f}%</span>",
                            unsafe_allow_html=True,
                        )
                        st.caption("Peek behind the score: see how your categories shape this match.")
                    with b:
                        with st.popover("ℹ️"):
                            w_unit = weights_to_unit(st.session_state.get("weights", {}))
                            contrib = {
                                "Safety": float(row.get("safety_tugo_score", 0.0)) * float(w_unit.get("safety_tugo", 0.0)),
                                "Cost": float(row.get("cost_score", 0.0)) * float(w_unit.get("cost", 0.0)),
                                "Restaurant": float(row.get("restaurant_value_score", 0.0)) * float(w_unit.get("restaurant", 0.0)),
                                "Groceries": float(row.get("groceries_value_score", 0.0)) * float(w_unit.get("groceries", 0.0)),
                                "Rent": float(row.get("rent_score", 0.0)) * float(w_unit.get("rent", 0.0)),
                                "Purchasing power": float(row.get("purchasing_power_score", 0.0)) * float(w_unit.get("purchasing_power", 0.0)),
                                "Quality of Life": float(row.get("qol_score", 0.0)) * float(w_unit.get("qol", 0.0)),
                                "Healthcare": float(row.get("health_care_score", 0.0)) * float(w_unit.get("health_care", 0.0)),
                                "Clean Air": float(row.get("clean_air_score", 0.0)) * float(w_unit.get("clean_air", 0.0)),
                                "Culture": float(row.get("culture_score", 0.0)) * float(w_unit.get("culture", 0.0)),
                                "Weather": float(row.get("weather_score", 0.0)) * float(w_unit.get("weather", 0.0)),
                                "Luxury": float(row.get("luxury_price_score", 0.0)) * float(w_unit.get("luxury_price", 0.0)),
                                "Hidden Gem": float(row.get("hidden_gem_score", 0.0)) * float(w_unit.get("hidden_gem", 0.0)),
                                "Astro": float(row.get("astro_score", 0.0)) * float(w_unit.get("astro", 0.0)),
                                "Chaos Jitter": float(row.get("jitter_score", 0.0)) * float(w_unit.get("jitter", 0.0)),
                            }
                            for cat, val in sorted(contrib.items(), key=lambda x: x[1], reverse=True):
                                if val > 0.001:
                                    st.write(f"{cat}: {val*100:.1f}%")

                    flight_price = row.get("flight_price")
                    symbol = st.session_state.get("currency_symbol", "€")
                    rate = st.session_state.get("currency_rate", 1.0)
                    if flight_price and pd.notna(flight_price):
                        converted_price = float(flight_price) * rate
                        tooltip = f"Round trip for 1 adult from {row.get('flight_origin', 'your origin')} to {row.get('flight_dest', 'destination')}"
                        st.markdown(f"✈️ **Est. Flight:** {symbol}{converted_price:.0f}", help=tooltip)

                with c3:
                    if st.button("View Details", key=f"details_{row['iso2']}_{i}"):
                        st.session_state["selected_country"] = row.to_dict()
                        st.session_state.step = 7
                        st.rerun()


def show_dashboard_step(data_manager):
    """Country dashboard with Back & Start Over buttons TOP CORNERS"""
    
    country = st.session_state.get('selected_country')
    if not country:
        st.error("No country selected. Please go back to results.")
        if st.button("Back to Results"):
            st.session_state.step = 6
            st.rerun()
        return

    st.markdown("---")

    render_country_overview(
        country=country,
        data_manager=data_manager,
        openai_client=get_openai_client(),
        amadeus=amadeus,
        amadeus_api_key=AMADEUS_API_KEY,
        amadeus_api_secret=AMADEUS_API_SECRET,
        trip_planner_render=show_trip_planner
    )
# ============================================================
# APP ROUTER
# ============================================================
def run_app():

    setup_complete_design()
    render_pathfind_header()

    load_heavy_libs_dynamically()
    data_manager = DataManager()
    init_session_state()


    handle_google_oauth_callback(
        data_manager=data_manager,
        calendar_client=calendar_client,
        google_client_id=GOOGLE_CLIENT_ID,
        google_client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
    )

    require_login()

    step = st.session_state.step

    if step == 1:
        show_basic_info_step(data_manager)
    elif step == 2:
        render_persona_step(data_manager)
    elif step == 3:
        show_swiping_step()
    elif step == 4:
        show_astro_step(data_manager)
    elif step == 5:
        show_ban_choices_step(data_manager)
    elif step == 5.1:
        show_ban_list_step(data_manager)
    elif step == 6:
        show_results_step(data_manager)
    elif step == 7:
        show_dashboard_step(data_manager)
    elif step == 8:
        show_booking_step(
            amadeus=amadeus,
            amadeus_api_key=AMADEUS_API_KEY,
            amadeus_api_secret=AMADEUS_API_SECRET,
        )
    elif step == 9:
        show_confirmation_step(
            data_manager=data_manager,
            calendar_client=calendar_client,
            google_client_id=GOOGLE_CLIENT_ID,
            google_client_secret=GOOGLE_CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
        )
    elif step == "about":
        render_about_page()
        if st.button("← Back", use_container_width=False):
            # Zurück zum vorherigen step
            st.session_state.step = st.session_state.get("previous_step", 1)
            st.rerun()
        st.stop()

    render_footer()


if __name__ == "__main__":
    run_app()
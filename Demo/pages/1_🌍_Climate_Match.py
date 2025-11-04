# app_climate_dashboard.py
import json
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

# st.set_page_config(page_title="Climate Match — Countries", page_icon="🌍", layout="wide")
st.title("🌍 Climate Match — Find Countries by Monthly Climate")

# ----------------------- Config (fixed weights) -----------------------
WEIGHTS = {
    "temp": 0.5,     # Temperatur zählt 50 %
    "sun": 0.3,      # Sonne (Cloud-Proxy, niedriger = sonniger) 30 %
    "precip": 0.2,   # Niederschlag 20 %
}
TEMP_PENALTY_PER_DEG = 7.0  # 1°C Abweichung = −7 Punkte (fein justierbar)
TOP_K_DEFAULT = 10

PRECIP_LEVELS = ["very dry", "dry", "moderate", "wet", "very wet"]
SUN_LEVELS    = ["very sunny", "sunny", "partly sunny", "cloudy", "very cloudy"]
SUN_HINT = "(lower cloud % = sunnier)"

MONTHS = [
    ("January", 1), ("February", 2), ("March", 3), ("April", 4),
    ("May", 5), ("June", 6), ("July", 7), ("August", 8),
    ("September", 9), ("October", 10), ("November", 11), ("December", 12),
]

# ----------------------- Data loader -----------------------
@st.cache_data(show_spinner=True)
def load_json_flat(path: str) -> pd.DataFrame:
    """
    Erwartet Schema:
      {
        "metadata": {...},
        "countries": [
          {"country": "Germany", "months": [
              {"month":1,"temp_c_clim":..,"cloud_pct":..,"precip_mm":..,"precip_cat5":"..","sun_cat5":".."},
              ...
          ]},
          ...
        ]
      }
    Flacht es in DataFrame: country, month, temp_c_clim, cloud_pct, precip_mm, precip_cat5, sun_cat5
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows: List[Dict] = []
    for c in data.get("countries", []):
        name = c.get("country")
        for m in c.get("months", []):
            rows.append({
                "country": name,
                "month": m.get("month"),
                "temp_c_clim": m.get("temp_c_clim"),
                "cloud_pct": m.get("cloud_pct"),
                "precip_mm": m.get("precip_mm"),
                "precip_cat5": m.get("precip_cat5"),
                "sun_cat5": m.get("sun_cat5"),
            })
    df = pd.DataFrame(rows)
    # Typen & Tidy
    if not df.empty:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
        df["temp_c_clim"] = pd.to_numeric(df["temp_c_clim"], errors="coerce")
        df["cloud_pct"] = pd.to_numeric(df["cloud_pct"], errors="coerce")
        df["precip_mm"] = pd.to_numeric(df["precip_mm"], errors="coerce")
        df["country"] = df["country"].astype(str)
    return df

# ----------------------- Scoring -----------------------
def level_index(series: pd.Series, ordered_levels: List[str]) -> pd.Series:
    """Mappt kategoriale Labels auf 0..n-1; unbekannt/NaN -> NaN."""
    mapper = {lab: i for i, lab in enumerate(ordered_levels)}
    return series.map(mapper)

def compute_scores(sub: pd.DataFrame, target_temp: float, want_precip_level: int, want_sun_level: int) -> pd.DataFrame:
    """
    Gibt DataFrame mit 'score', Teil-Scores und Kennzahlen zurück.
    - Temperatur-Score (0..100): 100 - k*|ΔT|, geclippt
    - Precip/Sun-Score (0..100): 100 - 50*dist (0..4) / 2 → 0, 25, 50, 75, 100? (wir nehmen 0..100 linear)
      hier linear: 100 - 25 * |level_diff| (=> exakt passend 100, 1 Stufe diff 75, ... bis 0)
    Gesamt: gewichtete Summe.
    """
    df = sub.copy()

    # Temp
    df["abs_diff_temp"] = (df["temp_c_clim"] - float(target_temp)).abs()
    df["score_temp"] = (100.0 - TEMP_PENALTY_PER_DEG * df["abs_diff_temp"]).clip(lower=0, upper=100)

    # Kategorial → Index
    df["precip_idx"] = level_index(df["precip_cat5"], PRECIP_LEVELS)
    df["sun_idx"]    = level_index(df["sun_cat5"],    SUN_LEVELS)

    # Abstand in Kategorien
    df["precip_dist"] = (df["precip_idx"] - want_precip_level).abs()
    df["sun_dist"]    = (df["sun_idx"] - want_sun_level).abs()

    # Lineare Abwertung je Stufe
    df["score_precip"] = (100.0 - 25.0 * df["precip_dist"]).clip(lower=0, upper=100)
    df["score_sun"]    = (100.0 - 25.0 * df["sun_dist"]).clip(lower=0, upper=100)

    # Gesamt (fixe Gewichte)
    df["score"] = (
        WEIGHTS["temp"]   * df["score_temp"] +
        WEIGHTS["sun"]    * df["score_sun"] +
        WEIGHTS["precip"] * df["score_precip"]
    ).round(1)

    # Aufräumen/Sortierung
    cols = [
        "country", "month", "temp_c_clim", "abs_diff_temp",
        "precip_mm", "cloud_pct", "precip_cat5", "sun_cat5",
        "score_temp", "score_sun", "score_precip", "score"
    ]
    return df[cols].sort_values(["score", "country"], ascending=[False, True])

# ----------------------- UI Controls (top area) -----------------------
st.subheader("Your selection", anchor=False)

# Fix: Keine Dateiauswahl nötig → Datensatz ist fest
DATA_PATH = "country_monthly_climate_2005_2024.json"

with st.spinner("Loading country climate dataset (2005–2024)…"):
    df_all = load_json_flat(DATA_PATH)

if df_all.empty:
    st.error("Dataset appears to be empty. Please regenerate the JSON.")
    st.stop()

# Controls (oben, nicht in Sidebar)
c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1])

month_label = c1.selectbox("Month", [m[0] for m in MONTHS], index=6)
MONTH = dict(MONTHS)[month_label]

target_temp = c2.slider("Target temperature (°C)", min_value=-10.0, max_value=40.0, value=24.0, step=0.5)

precip_level = c3.slider(
    "Precipitation preference (0–4)",
    min_value=0, max_value=4, value=2,
    help="0=very dry … 4=very wet"
)
sun_level = c4.slider(
    f"Sun preference (0–4) {SUN_HINT}",
    min_value=0, max_value=4, value=1,
    help="0=very sunny … 4=very cloudy"
)

# Top K (kleiner Selector unter den Controls)
top_k = st.number_input("Top K countries", min_value=1, max_value=100, value=TOP_K_DEFAULT, step=1, key="topk")

# ----------------------- Compute -----------------------
sub = df_all[df_all["month"] == MONTH].copy()

if sub.empty:
    st.warning("No rows for the selected month in the dataset.")
    st.stop()

results = compute_scores(
    sub=sub,
    target_temp=target_temp,
    want_precip_level=precip_level,
    want_sun_level=sun_level
)

# ----------------------- Display: Top list -----------------------
st.markdown("### Top matches")

top = results.head(int(top_k)).reset_index(drop=True)

st.dataframe(
    top.rename(columns={
        "country": "Country",
        "temp_c_clim": "Temp (°C)",
        "abs_diff_temp": "|ΔT| (°C)",
        "precip_mm": "Precip (mm)",
        "cloud_pct": "Cloud (%)",
        "precip_cat5": "Precip level",
        "sun_cat5": "Sun level",
        "score_temp": "Score (Temp)",
        "score_sun": "Score (Sun)",
        "score_precip": "Score (Precip)",
        "score": "Score (Total)"
    }),
    width="stretch"
)

# ----------------------- Map -----------------------
st.markdown("### World map (colored by score)")

# Für die Karte reicht Ländername → Plotly kann 'country names'
map_df = results[["country", "score"]].copy()
map_df = map_df.dropna(subset=["country"]).drop_duplicates(subset=["country"])

fig = px.choropleth(
    map_df,
    locations="country",
    locationmode="country names",
    color="score",
    color_continuous_scale="Viridis",
    range_color=(0, 100),
    title=f"Scores for {month_label}",
)
fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(title="Score"),
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------- Info expander -----------------------
with st.expander("ℹ️ How the score is computed / data notes"):
    st.markdown(f"""
**Scoring (fixed weights):**  
- Temperature match: **{WEIGHTS['temp']*100:.0f}%** of total — 100 − {TEMP_PENALTY_PER_DEG:g} × |Δ°C| (clipped 0–100)  
- Sun (cloud proxy): **{WEIGHTS['sun']*100:.0f}%** — categorical distance (0..4) → 100, 75, 50, 25, 0  
- Precipitation: **{WEIGHTS['precip']*100:.0f}%** — categorical distance (0..4) → 100, 75, 50, 25, 0

**Sun proxy:** We use **cloud cover %** (lower = sunnier).  
**Data period:** monthly country averages **2005–2024** (CRU CY v4.09).  
**JSON schema expected:**  
`countries[ {{country, months: [ {{month, temp_c_clim, cloud_pct, precip_mm, precip_cat5, sun_cat5}} ]}} ]`.  
    """)


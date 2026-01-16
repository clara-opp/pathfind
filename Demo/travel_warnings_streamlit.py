# travel_warnings_streamlit.py
# Streamlit app to visualize travel warning snapshot JSON.
# File expected next to this script: travelwarnings_snapshot.json

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------
# Config & constants
# -----------------------
DATA_FILE = Path(__file__).with_name("travelwarnings_snapshot.json")

SEVERITY_LABELS = {
    3: "Warning",
    2: "Partial warning",
    1: "Situation note",
    0: "None",
}

CATEGORY_ORDER = ["Warning", "Partial warning", "Situation note", "None"]
COLOR_MAP = {
    "Warning": "#d62728",          # red
    "Partial warning": "#ff7f0e",  # orange
    "Situation note": "#1f77b4",   # blue
    "None": "#16cf16",             # green
}


# -----------------------
# Data loading
# -----------------------
@st.cache_data(show_spinner=False)
def load_data_source() -> tuple[pd.DataFrame, str]:
    if not DATA_FILE.exists():
        st.error(f"Data file not found: {DATA_FILE}")
        return pd.DataFrame(), str(DATA_FILE)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)

    # Ensure expected columns exist
    for col in [
        "content_id",
        "title",
        "country_name",
        "country_code",
        "iso3_country_code",
        "last_modified_iso",
        "effective_iso",
        "warning",
        "partial_warning",
        "situation_warning",
        "situation_part_warning",
    ]:
        if col not in df.columns:
            df[col] = np.nan

    # Parse datetimes (timezone-aware UTC)
    for dtcol in ["last_modified_iso", "effective_iso"]:
        df[dtcol] = pd.to_datetime(df[dtcol], utc=True, errors="coerce")

    # Flags -> int (fill missing with 0)
    flag_cols = ["warning", "partial_warning", "situation_warning", "situation_part_warning"]
    df[flag_cols] = df[flag_cols].fillna(0).astype(int)

    # Severity (3>2>1>0)
    df["severity"] = np.select(
        [
            df["warning"].eq(1),
            df["partial_warning"].eq(1),
            df["situation_warning"].eq(1) | df["situation_part_warning"].eq(1),
        ],
        [3, 2, 1],
        default=0,
    ).astype(int)
    df["severity_label"] = df["severity"].map(SEVERITY_LABELS)

    # Category for plotting/table
    cat_series = np.select(
        [
            df["warning"].eq(1),
            df["partial_warning"].eq(1),
            df["situation_warning"].eq(1) | df["situation_part_warning"].eq(1),
        ],
        ["Warning", "Partial warning", "Situation note"],
        default="None",
    )
    df["category"] = pd.Categorical(cat_series, categories=CATEGORY_ORDER, ordered=True)

    # Month label for charts (avoid Period tz drop warnings)
    lm = df["last_modified_iso"]
    df["month_label"] = np.where(
        lm.notna(),
        lm.dt.tz_convert(UTC).dt.strftime("%Y-%m"),
        pd.NA,
    )

    return df, str(DATA_FILE)


# -----------------------
# UI
# -----------------------
st.set_page_config(
    page_title="Travel Warnings Dashboard",
    page_icon="🌍",
    layout="wide",
)

df, src = load_data_source()

st.title("🌍 Travel Warnings Dashboard")
st.caption(
    f"Data source: **{src}**  •  Rows: **{len(df)}**  •  Generated: "
    f"**{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}**"
)

if df.empty:
    st.stop()

# -----------------------
# Top KPIs
# -----------------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Total countries", len(df))
with c2:
    st.metric("Warnings", int(df["warning"].sum()))
with c3:
    st.metric("Partial warnings", int(df["partial_warning"].sum()))
with c4:
    st.metric(
        "Situation notes",
        int((df["situation_warning"].eq(1) | df["situation_part_warning"].eq(1)).sum()),
    )
with c5:
    st.metric("No issues", int((df["severity"] == 0).sum()))

st.markdown("---")

# -----------------------
# Monthly stacked bar
# -----------------------
monthly = (
    df.groupby(["month_label", "category"], dropna=False)
    .size()
    .reset_index(name="countries")
)

fig = px.bar(
    monthly,
    x="month_label",
    y="countries",
    color="category",
    category_orders={"category": CATEGORY_ORDER},
    color_discrete_map=COLOR_MAP,
    title="Updates by Month (stacked by category)",
)
fig.update_layout(
    xaxis_title="Month",
    yaxis_title="Countries",
    legend_title="Category",
    bargap=0.2,
    height=380,
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# -----------------------
# Filters
# -----------------------
left, right = st.columns([2, 3])
with left:
    sel_sev = st.multiselect(
        "Filter by severity",
        options=[SEVERITY_LABELS[s] for s in sorted(SEVERITY_LABELS.keys(), reverse=True)],
        default=[SEVERITY_LABELS[3], SEVERITY_LABELS[2], SEVERITY_LABELS[1], SEVERITY_LABELS[0]],
    )
    sel_text = st.text_input("Search title/country", "")

# Apply filters
fdf = df.copy()
if sel_sev:
    fdf = fdf[fdf["severity_label"].isin(sel_sev)]
if sel_text.strip():
    pat = sel_text.strip().lower()
    fdf = fdf[
        fdf["country_name"].str.lower().str.contains(pat, na=False)
        | fdf["title"].str.lower().str.contains(pat, na=False)
        | fdf["country_code"].str.lower().str.contains(pat, na=False)
    ]

# -----------------------
# World map (CHOROPLETH)
# -----------------------
st.subheader("World map")
map_df = fdf.copy()

# Keep valid ISO3 codes (Plotly needs ISO-3)
map_df = map_df[map_df["iso3_country_code"].astype(str).str.len() == 3].copy()

fig_map = px.choropleth(
    map_df,
    locations="iso3_country_code",
    color="category",
    hover_name="country_name",
    hover_data={
        "iso3_country_code": False,
        "country_code": True,
        "severity": True,
        "title": True,
        "last_modified_iso": True,
    },
    category_orders={"category": CATEGORY_ORDER},
    color_discrete_map=COLOR_MAP,
    projection="natural earth",
    title="Current advisory status by country",
)
fig_map.update_layout(
    legend_title="Category",
    height=520,
    margin=dict(l=10, r=10, t=60, b=10),
)
st.plotly_chart(fig_map, use_container_width=True)

st.markdown("---")

# -----------------------
# Countries table
# -----------------------
st.subheader("Countries")

needed = ["severity", "severity_label", "country_name", "country_code", "last_modified_iso", "title"]
for c in needed:
    if c not in fdf.columns:
        if c == "severity":
            fdf[c] = 0
        else:
            fdf[c] = ""

fdf = fdf.sort_values(["severity", "country_name"], ascending=[False, True], kind="mergesort")

present_cols = ["severity_label", "country_name", "country_code", "last_modified_iso", "title"]
st.dataframe(
    fdf[present_cols].rename(
        columns={
            "severity_label": "Severity",
            "country_name": "Country",
            "country_code": "ISO2",
            "last_modified_iso": "Last updated (UTC)",
            "title": "Advisory",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# -----------------------
# Download
# -----------------------
st.download_button(
    "Download filtered table (CSV)",
    data=fdf[present_cols].to_csv(index=False).encode("utf-8"),
    file_name="travel_warnings_filtered.csv",
    mime="text/csv",
)

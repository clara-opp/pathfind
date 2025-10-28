# streamlit_app.py
import os
import pandas as pd
import streamlit as st

# Import from your robust module
from weather_search import (
    load_all_countries,
    find_top_countries_for_month_temp,
    normalize_month,   # optional (only if exposed in your file)
)

# --------- Page config ----------
st.set_page_config(page_title="Climate Match", page_icon="🌍", layout="wide")

st.title("🌍 Climate Match — Find Countries by Monthly Temperature")
st.caption(
    "Data source: Berkeley Earth (country monthly averages) "
    "(via compgeolab mirror by default, or original ZIP if `USE_BERKELEY_ORIGINAL=1`)."
)

# --------- Cached data loader ----------
@st.cache_data(show_spinner=True)
def get_data():
    df = load_all_countries()
    # Keep only necessary columns and ensure types
    df = df[["country", "year", "month", "temp_c"]].copy()
    df["country"] = df["country"].astype(str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    df["temp_c"] = pd.to_numeric(df["temp_c"], errors="coerce")
    return df

with st.spinner("Loading country climate dataset… (cached after first run)"):
    df = get_data()

# --------- Sidebar controls ----------
st.sidebar.header("Controls")

# Month list (English + German labels)
MONTHS = [
    ("January", 1), ("February", 2), ("March", 3), ("April", 4),
    ("May", 5), ("June", 6), ("July", 7), ("August", 8),
    ("September", 9), ("October", 10), ("November", 11), ("December", 12),
]
month_label = st.sidebar.selectbox("Month", [m[0] for m in MONTHS], index=6)  # default July
month = dict(MONTHS)[month_label]

# Temperature slider (global sensible range)
target_temp = st.sidebar.slider("Target temperature (°C)", min_value=-10.0, max_value=40.0, value=24.0, step=0.1)

top_k = st.sidebar.number_input("Top K countries", min_value=1, max_value=50, value=10, step=1)

run_btn = st.sidebar.button("Find countries")

# --------- Main area ----------
st.subheader("Your selection")
st.write(f"**Month:** {month_label}  •  **Target:** {target_temp:.1f} °C  •  **Top K:** {top_k}")

def compute_results():
    res = find_top_countries_for_month_temp(
        df=df,
        month=month,
        target_temp_c=float(target_temp),
        top_k=int(top_k),
        min_years=10,
        agg="mean",
    ).reset_index(drop=True)

    # Optional: add a simple 0–100 score based on abs diff (you can tune later)
    # Here: every 1°C difference costs 7 points, clipped to [0,100]
    res["score"] = (100 - 7 * res["abs_diff"]).clip(lower=0, upper=100).round(1)
    # Nice column order
    res = res[["country", "month", "temp_c_clim", "abs_diff", "n_years", "score"]]
    return res

if run_btn:
    try:
        results = compute_results()

        if results.empty:
            st.warning("No matches found with the chosen filters.")
        else:
            st.success("Here are your top matches:")
            st.dataframe(results, use_container_width=True)

            # Bar chart of scores
            chart_df = results[["country", "score"]].set_index("country")
            st.bar_chart(chart_df)

            # Download CSV
            csv = results.to_csv(index=False).encode("utf-8")
            st.download_button("Download results as CSV", data=csv, file_name="climate_match_results.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error: {e}")

# --------- Footer / Tips ----------
with st.expander("ℹ️ Tips / Notes"):
    st.markdown("""
- Data are monthly **country averages** over many years. We aggregate all available years for the chosen month.
- `n_years` shows how many year-samples contributed to the climate average in that month for that country.
- Switch to the **original Berkeley ZIP** by running Streamlit with:
- First run downloads & caches the ZIP locally; subsequent runs are fast.
""")

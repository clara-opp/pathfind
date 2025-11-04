import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------
# Streamlit page setup
# -------------------------------------------------------
st.set_page_config(page_title="Euro Value & Exchange Trends", layout="wide")

st.title("🌍 Euro Purchasing Power & Exchange Rate Dashboard")
st.markdown("""
This interactive dashboard lets you explore:
1. 💶 **Euro purchasing power (EuroValue)** based on PPP and exchange rate data.  
2. 📈 **Exchange rate trends** over time for each country (LCU per USD).

_Data sources: World Bank ICP & WDI_
""")

# =======================================================
# LOAD DATA
# =======================================================
@st.cache_data
def load_pli_data():
    df = pd.read_csv("pli_data.csv")
    df = df.dropna(subset=["EuroValue"])
    df["country_code"] = df["country_code"].astype(str).str.strip().str.upper()
    return df

@st.cache_data
def load_exchange_data():
    df = pd.read_csv("exchange_data_full.csv")
    year_cols = [c for c in df.columns if c.isdigit()]
    df_long = df.melt(
        id_vars=["country_code", "country_name"],
        value_vars=year_cols,
        var_name="year",
        value_name="exchange_rate"
    )
    df_long["year"] = pd.to_numeric(df_long["year"], errors="coerce")
    df_long["exchange_rate"] = pd.to_numeric(df_long["exchange_rate"], errors="coerce")

    # interpolate missing values within each country
    df_long = (
        df_long.sort_values(["country_name", "year"])
        .groupby("country_name")
        .apply(lambda x: x.interpolate(limit_direction="both"))
        .reset_index(drop=True)
    )
    return df_long

pli = load_pli_data()
fx = load_exchange_data()

# =======================================================
# TABS
# =======================================================
tab1, tab2 = st.tabs(["💶 Euro Value Map", "📈 Exchange Rate Trends"])

# -------------------------------------------------------
# TAB 1 – Euro Value Map
# -------------------------------------------------------
with tab1:
    st.subheader("💶 Euro Purchasing Power by Country")
    st.markdown("""
    A higher **EuroValue** means your Euro buys **more goods and services** 
    relative to Germany (based on PPP and exchange rate data).
    """)

    # Choropleth Map
    fig = px.choropleth(
        pli,
        locations="country_code",
        locationmode="ISO-3",
        color="EuroValue",
        hover_name="country_name",
        color_continuous_scale=["#ff4d4d", "#ffff99", "#009933"],
        range_color=(pli["EuroValue"].quantile(0.05), pli["EuroValue"].quantile(0.95)),
        projection="natural earth",
        title="Euro Purchasing Power by Country",
    )

    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        coloraxis_colorbar=dict(
            title="Euro Value (× relative to Germany)",
            tickprefix="× ",
            len=0.75,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Rankings
    st.markdown("### 🏆 Rankings")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("💰 **Top 10 countries where the Euro is most valuable**")
        st.dataframe(
            pli.nlargest(10, "EuroValue")[["country_name", "EuroValue"]].reset_index(drop=True),
            use_container_width=True
        )
    with col2:
        st.markdown("🔴 **Top 10 countries where the Euro is least valuable**")
        st.dataframe(
            pli.nsmallest(10, "EuroValue")[["country_name", "EuroValue"]].reset_index(drop=True),
            use_container_width=True
        )

# -------------------------------------------------------
# TAB 2 – Exchange Rate Trends
# -------------------------------------------------------
with tab2:
    st.subheader("📈 Exchange Rate Trends by Country")
    st.markdown("""
    **Exchange rate (LCU per USD):**  
    How many local currency units (LCU) are needed to buy 1 US dollar.  
    Smaller values = stronger currency, larger values = weaker currency.
    """)

    # Sidebar filter for countries
    countries = sorted(fx["country_name"].unique())
    selected_countries = st.multiselect(
        "Select countries to display:",
        options=countries,
        default=["Germany"] if "Germany" in countries else countries[:2]
    )

    filtered = fx[fx["country_name"].isin(selected_countries)]

    # Plot exchange rates
    fig_fx = px.line(
        filtered,
        x="year",
        y="exchange_rate",
        color="country_name",
        markers=True,
        title="Exchange Rate Trends (LCU per USD)",
    )

    fig_fx.update_traces(mode="lines+markers", hovertemplate="%{x}: %{y:.2f}")
    fig_fx.update_layout(
        xaxis_title="Year",
        yaxis_title="Exchange Rate (LCU per USD)",
        hovermode="x unified",
        legend_title="Country",
        template="plotly_white",
        margin=dict(l=0, r=0, t=60, b=0),
    )
    st.plotly_chart(fig_fx, use_container_width=True)

    # Summary table
    st.markdown("### 📊 Summary Statistics (per country)")
    summary = filtered.groupby("country_name")["exchange_rate"].describe().round(3)
    st.dataframe(summary, use_container_width=True)

# -------------------------------------------------------
# Footer
# -------------------------------------------------------
st.markdown("---")
st.caption("Data: World Bank ICP 2021 & WDI • Visualization by Fritz Bumb 🌞")

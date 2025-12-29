"""
Unified Country Database Creator - FIXED VERSION WITH FULL TUGO & NUMBEO DATA

This script merges multiple country-related datasets into a single SQLite database.
It creates:
    - countries (master table, joined on iso3)
    - climate_monthly
    - unesco_heritage_sites
    - unesco_by_country
    - tugo_* detail tables (climate, health, safety, laws, entry, offices)
    - numbeo_prices, numbeo_items, numbeo_exchange_rates, numbeo_indices
    - airports, flight_costs
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd


# ======================================================================
# Helper: locate data files
# ======================================================================

def get_data_path(filename: str) -> str:
    """Return the path to a data file, searching in data/, script dir, parent."""
    script_dir = Path(__file__).parent

    # Priority 1: data subdirectory
    data_dir_path = script_dir / "data" / filename
    if data_dir_path.exists():
        return str(data_dir_path)

    # Priority 2: script directory
    file_path = script_dir / filename
    if file_path.exists():
        return str(file_path)

    # Priority 3: parent directory
    parent_path = script_dir.parent / filename
    if parent_path.exists():
        return str(parent_path)

    raise FileNotFoundError(f"Cannot find '{filename}'")


# ======================================================================
# ISO country codes (base table)
# ======================================================================

def load_iso_codes() -> pd.DataFrame:
    """Load ISO country codes as the base reference table (index: iso3)."""
    filepath = get_data_path("wikipedia-iso-country-codes.csv")
    df = pd.read_csv(filepath)
    df = df.rename(
        columns={
            "English short name lower case": "country_name",
            "Alpha-2 code": "iso2",
            "Alpha-3 code": "iso3",
            "Numeric code": "numeric_code",
            "ISO 3166-2": "iso_3166_2",
        }
    )
    df = df.set_index("iso3")
    return df


# ======================================================================
# PLI and historical exchange rates
# ======================================================================

def load_pli_data() -> pd.DataFrame:
    """Load Price Level Index data (index: iso3, columns prefixed with pli_)."""
    filepath = get_data_path("pli_data.csv")
    df = pd.read_csv(filepath)
    df = df.rename(columns={"country_code": "iso3"})
    if "country_name" in df.columns:
        df = df.drop(columns=["country_name"])
    df = df.set_index("iso3")
    df.columns = ["pli_" + col for col in df.columns]
    return df


def load_exchange_data() -> pd.DataFrame:
    """Load historical exchange rate data (index: iso3, columns exchange_rate_YYYY)."""
    filepath = get_data_path("exchange_data_full.csv")
    df = pd.read_csv(filepath)
    df = df.rename(columns={"country_code": "iso3"})
    if "country_name" in df.columns:
        df = df.drop(columns=["country_name"])
    df = df.set_index("iso3")

    year_columns = [col for col in df.columns if col.isdigit()]
    rename_dict = {col: f"exchange_rate_{col}" for col in year_columns}
    df = df.rename(columns=rename_dict)
    return df


# ======================================================================
# TuGo travel warnings (summary + details)
# ======================================================================

def load_tugo_travel_warnings_with_details():
    """
    Load TuGo travel warning data.

    Returns
    -------
    summary_df : DataFrame
        Summary information per country, indexed by iso3.
    detail_dfs : dict[str, DataFrame]
        Detail tables with iso2 as identifier:
            tugo_climate, tugo_health, tugo_safety,
            tugo_laws, tugo_entry, tugo_offices
    """
    try:
        filepath = get_data_path("tugo_travelwarnings.json")
    except FileNotFoundError:
        try:
            filepath = get_data_path("all_travel_warnings.json")
        except FileNotFoundError:
            print("  [INFO] TuGo travel warnings file not found, skipping TuGo data.")
            return pd.DataFrame(), {}

    print(f"  Loading TuGo data from: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  Found {len(data)} countries in TuGo data")

    summary_records = []
    climate_records = []
    health_records = []
    safety_records = []
    laws_records = []
    entry_records = []
    offices_records = []

    for country in data:
        iso2 = country.get("code")
        country_name = country.get("name")

        if not iso2:
            print(f"  [WARNING] Country without ISO2 code: {country_name}")
            continue

        # Summary record
        summary_records.append(
            {
                "iso2": iso2,
                "tugo_country_name": country_name,
                "tugo_advisory_state": country.get("advisoryState"),
                "tugo_advisory_text": country.get("advisoryText"),
                "tugo_has_warning": int(bool(country.get("hasAdvisoryWarning"))),
                "tugo_has_regional": int(bool(country.get("hasRegionalAdvisory"))),
                "tugo_published_date": country.get("publishedDate"),
                "tugo_recent_updates": country.get("recentUpdates"),
                "tugo_advisories_desc": country.get("advisories", {}).get("description"),
            }
        )

        # Climate info
        climate_info = country.get("climate", {}).get("climateInfo", [])
        for item in climate_info:
            climate_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )

        # Health info
        health_info = country.get("health", {})

        diseases = health_info.get("diseasesAndVaccinesInfo", {})
        for disease_name, disease_info_list in diseases.items():
            for disease_info in disease_info_list:
                health_records.append(
                    {
                        "iso2": iso2,
                        "country_name": country_name,
                        "disease_name": disease_name,
                        "category": disease_info.get("category", ""),
                        "description": disease_info.get("description"),
                    }
                )

        for item in health_info.get("healthInfo", []):
            health_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "disease_name": "GENERAL",
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )

        # Safety info
        safety_info = country.get("safety", {}).get("safetyInfo", [])
        for item in safety_info:
            safety_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )

        # Law and culture
        law_info = country.get("lawAndCulture", {}).get("lawAndCultureInfo", [])
        for item in law_info:
            laws_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )

        # Entry/exit requirements
        entry_info = country.get("entryExitRequirement", {})
        for item in entry_info.get("requirementInfo", []):
            entry_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "category": item.get("category"),
                    "description": item.get("description"),
                }
            )

        # Offices
        for office in country.get("offices", []):
            offices_records.append(
                {
                    "iso2": iso2,
                    "country_name": country_name,
                    "office_type": office.get("type"),
                    "city": office.get("city"),
                    "address": office.get("address"),
                    "phone": office.get("phone"),
                    "email": office.get("email1"),
                    "website": office.get("website"),
                }
            )

    summary_df = pd.DataFrame(summary_records)

    # Map ISO2 -> ISO3 for summary
    iso_map = load_iso_codes().reset_index()[["iso2", "iso3"]]
    summary_df = summary_df.merge(iso_map, on="iso2", how="left")
    summary_df = summary_df.drop(columns=["iso2"])
    summary_df = summary_df.set_index("iso3")

    climate_df = pd.DataFrame(climate_records)
    health_df = pd.DataFrame(health_records)
    safety_df = pd.DataFrame(safety_records)
    laws_df = pd.DataFrame(laws_records)
    entry_df = pd.DataFrame(entry_records)
    offices_df = pd.DataFrame(offices_records)

    print("  Extracted TuGo detail records:")
    print(f"    - Climate: {len(climate_df)}")
    print(f"    - Health: {len(health_df)}")
    print(f"    - Safety: {len(safety_df)}")
    print(f"    - Laws: {len(laws_df)}")
    print(f"    - Entry: {len(entry_df)}")
    print(f"    - Offices: {len(offices_df)}")

    detail_dfs = {
        "tugo_climate": climate_df,
        "tugo_health": health_df,
        "tugo_safety": safety_df,
        "tugo_laws": laws_df,
        "tugo_entry": entry_df,
        "tugo_offices": offices_df,
    }

    return summary_df, detail_dfs


# ======================================================================
# German Foreign Office travel warnings
# ======================================================================

def load_foreign_office_travel_warnings() -> pd.DataFrame:
    """Load German Foreign Office travel warning data (index: iso3)."""
    try:
        filepath = get_data_path("foreign_office_travelwarnings.json")
    except FileNotFoundError:
        try:
            filepath = get_data_path("travelwarnings_snapshot.json")
        except FileNotFoundError:
            print("  [INFO] Foreign Office travel warnings file not found, skipping.")
            return pd.DataFrame()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.rename(columns={"iso3_country_code": "iso3"})
    cols_to_drop = ["country_code", "country_name"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    cols_to_prefix = [col for col in df.columns if col != "iso3"]
    df = df.rename(columns={col: f"fo_{col}" for col in cols_to_prefix})
    df = df.set_index("iso3")
    return df


# ======================================================================
# Climate data
# ======================================================================

def load_climate_data() -> pd.DataFrame:
    """Load monthly climate data from JSON, one row per country."""
    filepath = get_data_path("country_monthly_climate_2005_2024.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    countries_data = data["countries"]
    climate_records = []

    for country_entry in countries_data:
        country_name = country_entry["country"]
        months = country_entry.get("months", [])
        if not months:
            continue

        temps = [m["temp_c_clim"] for m in months if m.get("temp_c_clim") is not None]
        clouds = [m["cloud_pct"] for m in months if m.get("cloud_pct") is not None]
        precips = [m["precip_mm"] for m in months if m.get("precip_mm") is not None]

        record = {
            "country_name_climate": country_name,
            "climate_avg_temp_c": sum(temps) / len(temps) if temps else None,
            "climate_avg_cloud_pct": sum(clouds) / len(clouds) if clouds else None,
            "climate_total_precip_mm": sum(precips) if precips else None,
            "climate_avg_monthly_precip_mm": (
                sum(precips) / len(precips) if precips else None
            ),
        }

        for month_data in months:
            month_num = month_data["month"]
            record[f"climate_temp_month_{month_num}"] = month_data.get("temp_c_clim")
            record[f"climate_cloud_month_{month_num}"] = month_data.get("cloud_pct")
            record[f"climate_precip_month_{month_num}"] = month_data.get("precip_mm")

        climate_records.append(record)

    df = pd.DataFrame(climate_records)
    return df


# ======================================================================
# UNESCO heritage sites and summary by country
# ======================================================================

def load_unesco_heritage_data() -> pd.DataFrame:
    """Load UNESCO World Heritage Sites data."""
    try:
        filepath = get_data_path("unesco_sites_full.json")
    except FileNotFoundError:
        print("  [WARNING] UNESCO heritage sites file not found, skipping.")
        return pd.DataFrame()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  Found {len(data)} UNESCO heritage sites")
    df = pd.DataFrame(data)
    return df


def load_unesco_by_country_data() -> pd.DataFrame:
    """Load summary of UNESCO World Heritage Sites by country."""
    try:
        filepath = get_data_path("unesco_by_country.json")
    except FileNotFoundError:
        print("  [WARNING] UNESCO by country file not found, skipping.")
        return pd.DataFrame()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  Found {len(data)} UNESCO country summary records")
    df = pd.DataFrame(data)

    if "site_names" in df.columns:
        df["site_names"] = df["site_names"].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else x
        )
    if "site_ids" in df.columns:
        df["site_ids"] = df["site_ids"].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else x
        )

    return df


# ======================================================================
# Numbeo data
# ======================================================================

def load_numbeo_countries() -> pd.DataFrame:
    """
    Load Numbeo country metadata: country_name, currency, iso3, country_param_used.

    Returns a DataFrame indexed by iso3 with:
        numbeo_country_name, numbeo_country_param_used, currency, ...
    """
    try:
        filepath = get_data_path("numbeo_countries.csv")
    except FileNotFoundError:
        print("  [INFO] numbeo_countries.csv not found, skipping Numbeo country metadata.")
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    df = df.rename(
        columns={
            "country_name": "numbeo_country_name",
            "country_param_used": "numbeo_country_param_used",
        }
    )

    if "iso3" not in df.columns:
        print("  [WARNING] numbeo_countries.csv has no iso3 column, skipping.")
        return pd.DataFrame()

    df = df.set_index("iso3")
    return df


def load_numbeo_prices() -> pd.DataFrame:
    """
    Load Numbeo country prices (large fact table).
    Will be stored as numbeo_prices, and used to derive numbeo_items.
    """
    try:
        filepath = get_data_path("numbeo_country_prices.csv")
    except FileNotFoundError:
        print("  [INFO] numbeo_country_prices.csv not found, skipping Numbeo prices.")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    return df


def load_numbeo_exchange_rates() -> pd.DataFrame:
    """
    Load Numbeo exchange rates (per currency).

    Returns a DataFrame indexed by currency if that column exists.
    """
    try:
        filepath = get_data_path("numbeo_exchange_rates.csv")
    except FileNotFoundError:
        print("  [INFO] numbeo_exchange_rates.csv not found, skipping Numbeo exchange rates.")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    if "currency" in df.columns:
        df = df.set_index("currency")
    return df


def load_numbeo_indices() -> pd.DataFrame:
    """
    Load Numbeo country indices (cost of living, quality of life, etc.).

    Requires an iso3 column. All metric columns are prefixed with 'numbeo_'.
    Returns a DataFrame indexed by iso3.
    """
    try:
        filepath = get_data_path("numbeo_country_indices.csv")
    except FileNotFoundError:
        print("  [INFO] numbeo_country_indices.csv not found, skipping Numbeo indices.")
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    if "iso3" not in df.columns:
        print("  [WARNING] numbeo_country_indices.csv has no iso3 column, skipping.")
        return pd.DataFrame()

    if "country_name" in df.columns:
        df = df.rename(columns={"country_name": "numbeo_country_name_indices"})

    rename_map = {}
    for col in df.columns:
        if col in ("iso3", "numbeo_country_name_indices"):
            continue
        rename_map[col] = f"numbeo_{col}"

    df = df.rename(columns=rename_map)
    df = df.set_index("iso3")
    return df

# ======================================================================
# Load Tarot Travel Database
# ======================================================================
def load_tarot_travel_database() -> pd.DataFrame:
    """Load tarot cards with country associations."""
    try:
        filepath = get_data_path("complete_tarot_travel_database.json")
    except FileNotFoundError:
        print("  [INFO] complete_tarot_travel_database.json not found, skipping Tarot data.")
        return pd.DataFrame()

    with open(filepath, "r", encoding="utf-8") as f:
        tarot_data = json.load(f)

    tarot_records = []

    # Process Major Arcana
    for card in tarot_data.get("major_arcana", []):
        for orientation in ["upright", "reversed"]:
            card_info = card.get(orientation, {})
            countries = card_info.get("countries", [])
            
            for country in countries:
                tarot_records.append({
                    "card_id": card["id"],
                    "card_name": card["name"],
                    "arcana_type": "major",
                    "orientation": orientation,
                    "country_code": country["code"],
                    "country_name": country["name"],
                    "reason": country.get("reason", ""),
                    "keywords": json.dumps(card_info.get("keywords", [])),
                    "travel_meaning": card_info.get("travel_meaning", ""),
                    "travel_style": card_info.get("travel_style", ""),
                })

    # Process Minor Arcana
    for suit, cards in tarot_data.get("minor_arcana", {}).items():
        for card in cards:
            for orientation in ["upright", "reversed"]:
                card_info = card.get(orientation, {})
                countries = card_info.get("countries", [])
                
                for country in countries:
                    tarot_records.append({
                        "card_id": card["id"],
                        "card_name": card["name"],
                        "arcana_type": f"minor_{suit}",
                        "orientation": orientation,
                        "country_code": country["code"],
                        "country_name": country["name"],
                        "reason": country.get("reason", ""),
                        "keywords": json.dumps(card_info.get("keywords", [])),
                        "travel_meaning": card_info.get("travel_meaning", ""),
                        "travel_style": card_info.get("travel_style", ""),
                    })

    df = pd.DataFrame(tarot_records)
    print(f"  Loaded {len(df)} tarot-country associations")
    return df



# ======================================================================
# Unsplash pictures
# ======================================================================

def load_pictures_data() -> pd.DataFrame:
    """
    Load Unsplash pictures. If pictures.json is missing, try to fetch it.

    Result: DataFrame indexed by iso3 with columns:
        img_1, credit_1, credit_url_1, img_2, ..., img_3, ...
    """
    filename = "pictures.json"

    try:
        filepath = get_data_path(filename)
        print(f"  Loading pictures from: {filepath}")
    except FileNotFoundError:
        print("  [INFO] pictures.json not found. Trying to fetch via unsplash_api...")
        try:
            from unsplash_api import fetch_country_images

            fetch_country_images()
            filepath = get_data_path(filename)
        except Exception as e:
            print(f"  [ERROR] Error fetching images: {e}")
            return pd.DataFrame()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            return pd.DataFrame()

        records = []
        for entry in data:
            record = {"iso3": entry["iso3"]}
            images = entry.get("images", [])

            for i in range(3):
                suffix = str(i + 1)
                if i < len(images):
                    img = images[i]
                    record[f"img_{suffix}"] = img.get("image_url")
                    record[f"credit_{suffix}"] = img.get("photographer_name")
                    record[f"credit_url_{suffix}"] = img.get("photographer_url")
                else:
                    record[f"img_{suffix}"] = None
                    record[f"credit_{suffix}"] = None
                    record[f"credit_url_{suffix}"] = None

            records.append(record)

        df = pd.DataFrame(records)
        df = df.set_index("iso3")
        return df

    except Exception as e:
        print(f"  [ERROR] Error reading pictures.json: {e}")
        return pd.DataFrame()


# ======================================================================
# Airports and flight network
# ======================================================================

def load_airports_data() -> pd.DataFrame:
    """Load airport data using amadeus_api.load_airport_data()."""
    try:
        from amadeus_api import load_airport_data

        return load_airport_data()
    except ImportError:
        print("  [INFO] amadeus_api.py not found. Skipping airports.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  [ERROR] Error loading airports: {e}")
        return pd.DataFrame()


def load_flight_network_data(airports_df: pd.DataFrame) -> pd.DataFrame:
    """Load flight cost data, depending on existing airport data."""
    if airports_df.empty:
        print("  [INFO] No airport data available. Skipping flight network.")
        return pd.DataFrame()

    try:
        from fetch_route_prices import get_flight_network_data

        return get_flight_network_data(airports_df)
    except ImportError:
        print("  [INFO] fetch_route_prices.py not found. Skipping flight network.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  [ERROR] Error loading flight network: {e}")
        return pd.DataFrame()


# ======================================================================
# Main: create unified SQLite database
# ======================================================================

def create_unified_database(output_db: str = "unified_country_database.db"):
    """Create a unified SQLite database from all data sources."""

    print("\n" + "=" * 60)
    print("UNIFIED COUNTRY DATABASE CREATOR - FIXED")
    print("=" * 60)
    print("\nLoading data sources...")

    print("  - ISO country codes (base table)")
    iso_df = load_iso_codes()

    print("  - PLI (Price Level Index) data")
    pli_df = load_pli_data()

    print("  - Exchange rate data")
    exchange_df = load_exchange_data()

    print("  - TuGo travel warnings with details")
    tugo_summary_df, tugo_detail_dfs = load_tugo_travel_warnings_with_details()

    print("  - Foreign Office travel warnings")
    fo_df = load_foreign_office_travel_warnings()

    print("  - Climate data")
    climate_df = load_climate_data()

    print("  - UNESCO World Heritage Sites")
    unesco_df = load_unesco_heritage_data()

    print("  - Numbeo countries / prices / exchange rates / indices")
    numbeo_countries_df = load_numbeo_countries()
    numbeo_prices_df = load_numbeo_prices()
    numbeo_exchange_df = load_numbeo_exchange_rates()
    numbeo_indices_df = load_numbeo_indices()

    print("  - UNESCO by country summary")
    unesco_by_country_df = load_unesco_by_country_data()

    print("  - Tarot Travel Database")
    tarot_df = load_tarot_travel_database()

    print("  - Unsplash country pictures")
    pictures_df = load_pictures_data()

    print("  - Airports data")
    airports_df = load_airports_data()
    if not airports_df.empty:
        # 1. Sort so that rows with page_rank values come first (NaNs go to the bottom)
        airports_df = airports_df.sort_values(by='page_rank', ascending=False)
        
        # 2. Now drop duplicates, keeping the first (the one with the rank)
        airports_df = airports_df.drop_duplicates(subset=['iata_code'], keep='first')

    print("  - Flight network data")
    flight_costs_df = load_flight_network_data(airports_df)

    # ------------------------------------------------------------------
    # Merge everything on iso3 for main "countries" table
    # ------------------------------------------------------------------
    print("\nMerging datasets on ISO3 country codes...")

    unified_df = iso_df.copy()
    unified_df = unified_df.join(pli_df, how="left")
    unified_df = unified_df.join(exchange_df, how="left")

    if not tugo_summary_df.empty:
        unified_df = unified_df.join(tugo_summary_df, how="left")

    if not fo_df.empty:
        unified_df = unified_df.join(fo_df, how="left")

    if not pictures_df.empty:
        unified_df = unified_df.join(pictures_df, how="left")

    if not numbeo_countries_df.empty:
        unified_df = unified_df.join(numbeo_countries_df, how="left")

    if not numbeo_indices_df.empty:
        unified_df = unified_df.join(numbeo_indices_df, how="left")

    unified_df = unified_df.reset_index()

    print(
        f"  Unified dataset created: {len(unified_df)} countries x {len(unified_df.columns)} columns"
    )

    # ------------------------------------------------------------------
    # Save all tables to SQLite
    # ------------------------------------------------------------------
    script_dir = Path(__file__).parent
    db_path = script_dir / output_db

    print(f"\nSaving to SQLite: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Main table
    unified_df.to_sql("countries", conn, if_exists="replace", index=False)
    print(f"  [OK] 'countries' table: {len(unified_df)} rows")

    # Climate table
    climate_df.to_sql("climate_monthly", conn, if_exists="replace", index=False)
    print(f"  [OK] 'climate_monthly' table: {len(climate_df)} rows")

    # UNESCO tables
    if not unesco_df.empty:
        unesco_df.to_sql("unesco_heritage_sites", conn, if_exists="replace", index=False)
        print(f"  [OK] 'unesco_heritage_sites' table: {len(unesco_df)} rows")
    else:
        print("  [INFO] 'unesco_heritage_sites' table skipped (no data).")

    if not unesco_by_country_df.empty:
        unesco_by_country_df.to_sql(
            "unesco_by_country", conn, if_exists="replace", index=False
        )
        print(f"  [OK] 'unesco_by_country' table: {len(unesco_by_country_df)} rows")
    else:
        print("  [INFO] 'unesco_by_country' table skipped (no data).")

    # Airports and flights
    if not airports_df.empty:
        airports_df.to_sql("airports", conn, if_exists="replace", index=False)
        print(f"  [OK] 'airports' table: {len(airports_df)} rows")
    else:
        print("  [INFO] 'airports' table skipped (no data).")

    if not flight_costs_df.empty:
        flight_costs_df.to_sql("flight_costs", conn, if_exists="replace", index=False)
        print(f"  [OK] 'flight_costs' table: {len(flight_costs_df)} rows")
    else:
        print("  [INFO] 'flight_costs' table skipped (no data).")

    
        # Tarot Travel Database
    if not tarot_df.empty:
        tarot_df.to_sql("tarot_countries", conn, if_exists="replace", index=False)
        print(f"  [OK] 'tarot_countries' table: {len(tarot_df)} rows")
    else:
        print("  [INFO] 'tarot_countries' table skipped (no data).")


    # Numbeo tables
    if not numbeo_prices_df.empty:
        numbeo_prices_df.to_sql("numbeo_prices", conn, if_exists="replace", index=False)
        print(f"  [OK] 'numbeo_prices' table: {len(numbeo_prices_df)} rows")

        # Derive numbeo_items (item_id -> item_name)
        if {"item_id", "item_name"}.issubset(numbeo_prices_df.columns):
            numbeo_items_df = (
                numbeo_prices_df[["item_id", "item_name"]]
                .drop_duplicates(subset=["item_id"])
                .sort_values("item_id")
            )
            numbeo_items_df.to_sql("numbeo_items", conn, if_exists="replace", index=False)
            print(f"  [OK] 'numbeo_items' table: {len(numbeo_items_df)} rows")
        else:
            print("  [INFO] 'numbeo_items' table skipped (no item_id/item_name).")
    else:
        print("  [INFO] 'numbeo_prices' table skipped (no data).")

    if not numbeo_exchange_df.empty:
        numbeo_exchange_df.reset_index().to_sql(
            "numbeo_exchange_rates", conn, if_exists="replace", index=False
        )
        print(f"  [OK] 'numbeo_exchange_rates' table: {len(numbeo_exchange_df)} rows")
    else:
        print("  [INFO] 'numbeo_exchange_rates' table skipped (no data).")

    if not numbeo_indices_df.empty:
        numbeo_indices_df.reset_index().to_sql(
            "numbeo_indices", conn, if_exists="replace", index=False
        )
        print(f"  [OK] 'numbeo_indices' table: {len(numbeo_indices_df)} rows")
    else:
        print("  [INFO] 'numbeo_indices' table skipped (no data).")

    # TuGo detail tables
    if tugo_detail_dfs:
        for table_name, df in tugo_detail_dfs.items():
            if not df.empty:
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                print(f"  [OK] '{table_name}' table: {len(df)} rows")

    # ------------------------------------------------------------------
    # Create indexes (only if table exists)
    # ------------------------------------------------------------------
    existing_tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    def create_index_if_table_exists(sql: str, table_name: str):
        if table_name in existing_tables:
            cursor.execute(sql)

    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_countries_iso3 ON countries(iso3)",
        "countries",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_climate_country ON climate_monthly(country_name_climate)",
        "climate_monthly",
    )

    # TuGo detail tables (iso2)
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_climate_iso2 ON tugo_climate(iso2)",
        "tugo_climate",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_health_iso2 ON tugo_health(iso2)",
        "tugo_health",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_safety_iso2 ON tugo_safety(iso2)",
        "tugo_safety",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_laws_iso2 ON tugo_laws(iso2)",
        "tugo_laws",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_entry_iso2 ON tugo_entry(iso2)",
        "tugo_entry",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tugo_offices_iso2 ON tugo_offices(iso2)",
        "tugo_offices",
    )

    # UNESCO
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_unesco_country_iso ON unesco_heritage_sites(country_iso)",
        "unesco_heritage_sites",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_unesco_id ON unesco_heritage_sites(id)",
        "unesco_heritage_sites",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_unesco_by_country_iso_code ON unesco_by_country(iso_code)",
        "unesco_by_country",
    )

    # Airports / flights
    create_index_if_table_exists(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code)",
        "airports",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_airports_iso2 ON airports(iso2)",
        "airports",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_flights_origin ON flight_costs(origin)",
        "flight_costs",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_flights_dest ON flight_costs(destination)",
        "flight_costs",
    )

    # Numbeo
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_numbeo_prices_iso3 ON numbeo_prices(iso3)",
        "numbeo_prices",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_numbeo_prices_item ON numbeo_prices(item_id)",
        "numbeo_prices",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_numbeo_items_id ON numbeo_items(item_id)",
        "numbeo_items",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_numbeo_exrates_currency ON numbeo_exchange_rates(currency)",
        "numbeo_exchange_rates",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_numbeo_indices_iso3 ON numbeo_indices(iso3)",
        "numbeo_indices",
    )

        # Tarot
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tarot_country_code ON tarot_countries(country_code)",
        "tarot_countries",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tarot_card_name ON tarot_countries(card_name)",
        "tarot_countries",
    )
    create_index_if_table_exists(
        "CREATE INDEX IF NOT EXISTS idx_tarot_orientation ON tarot_countries(orientation)",
        "tarot_countries",
    )


    conn.commit()
    print("  [OK] Indexes created")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("DATABASE CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nDatabase file: {db_path}")
    print("\nTables created:")
    print(f"  - countries ({len(unified_df)} rows)")
    print(f"  - climate_monthly ({len(climate_df)} rows)")
    if not unesco_df.empty:
        print(f"  - unesco_heritage_sites ({len(unesco_df)} rows)")
    if not unesco_by_country_df.empty:
        print(f"  - unesco_by_country ({len(unesco_by_country_df)} rows)")
    if not airports_df.empty:
        print(f"  - airports ({len(airports_df)} rows)")
    if not flight_costs_df.empty:
        print(f"  - flight_costs ({len(flight_costs_df)} rows)")
    if tugo_detail_dfs:
        for table_name, df in tugo_detail_dfs.items():
            if not df.empty:
                print(f"  - {table_name} ({len(df)} rows)")
    if not numbeo_prices_df.empty:
        print(f"  - numbeo_prices ({len(numbeo_prices_df)} rows)")
    if not numbeo_exchange_df.empty:
        print(f"  - numbeo_exchange_rates ({len(numbeo_exchange_df)} rows)")
    if not numbeo_indices_df.empty:
        print(f"  - numbeo_indices ({len(numbeo_indices_df)} rows)")
    if not tarot_df.empty:
        print(f"  - tarot_countries ({len(tarot_df)} rows)")


    print("\nExample queries:")
    print("  -- Get all Numbeo items:")
    print("  SELECT * FROM numbeo_items ORDER BY item_id;")
    print("\n  -- Get all TuGo health info for Afghanistan:")
    print("  SELECT * FROM tugo_health WHERE iso2 = 'AF';")
    print("\n  -- Join countries with Numbeo indices:")
    print("  SELECT country_name, numbeo_cost_of_living_index FROM countries LIMIT 10;")
    print("\n" + "=" * 60)

    conn.close()
    return unified_df, climate_df


if __name__ == "__main__":
    create_unified_database()

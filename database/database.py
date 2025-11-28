"""
Unified Country Database Creator - FIXED VERSION WITH FULL TUGO DATA

This script merges country datasets into SQLite database.
NOW includes complete TuGo data in separate detail tables.
"""

import pandas as pd
import json
import sqlite3
from pathlib import Path


def get_data_path(filename):
    """Get the correct path to a data file."""
    script_dir = Path(__file__).parent

    # Priority 1: Check 'data' subdirectory
    data_dir_path = script_dir / "data" / filename
    if data_dir_path.exists():
        return str(data_dir_path)

    # Priority 2: Check script directory
    file_path = script_dir / filename
    if file_path.exists():
        return str(file_path)

    # Priority 3: Check parent directory
    parent_path = script_dir.parent / filename
    if parent_path.exists():
        return str(parent_path)

    raise FileNotFoundError(f"Cannot find '{filename}'")


def load_iso_codes():
    """Load ISO country codes as the base reference table."""
    filepath = get_data_path('wikipedia-iso-country-codes.csv')
    df = pd.read_csv(filepath)
    df = df.rename(columns={
        'English short name lower case': 'country_name',
        'Alpha-2 code': 'iso2',
        'Alpha-3 code': 'iso3',
        'Numeric code': 'numeric_code',
        'ISO 3166-2': 'iso_3166_2'
    })
    df = df.set_index('iso3')
    return df


def load_pli_data():
    """Load Price Level Index data."""
    filepath = get_data_path('pli_data.csv')
    df = pd.read_csv(filepath)
    df = df.rename(columns={'country_code': 'iso3'})
    df = df.drop(columns=['country_name'])
    df = df.set_index('iso3')
    df.columns = ['pli_' + col for col in df.columns]
    return df


def load_exchange_data():
    """Load historical exchange rate data."""
    filepath = get_data_path('exchange_data_full.csv')
    df = pd.read_csv(filepath)
    df = df.rename(columns={'country_code': 'iso3'})
    df = df.drop(columns=['country_name'])
    df = df.set_index('iso3')
    year_columns = [col for col in df.columns if col.isdigit()]
    rename_dict = {col: f'exchange_rate_{col}' for col in year_columns}
    df = df.rename(columns=rename_dict)
    return df


def load_tugo_travel_warnings_with_details():
    """Load TuGo travel warning data - FIXED VERSION with detail extraction."""
    try:
        filepath = get_data_path('tugo_travelwarnings.json')
    except FileNotFoundError:
        try:
            filepath = get_data_path('all_travel_warnings.json')
        except FileNotFoundError:
            print("  ⚠️  TuGo travel warnings file not found, skipping...")
            return pd.DataFrame(), {}, []

    print(f"  Loading TuGo data from: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"  Found {len(data)} countries in TuGo data")

    # Main summary records
    summary_records = []

    # Detail records - USING ISO2 DIRECTLY (not converting to ISO3 yet)
    climate_records = []
    health_records = []
    safety_records = []
    laws_records = []
    entry_records = []
    offices_records = []

    for country in data:
        iso2 = country.get('code')
        country_name = country.get('name')

        if not iso2:
            print(f"  Warning: Country without ISO2 code: {country_name}")
            continue

        # Summary record
        summary = {
            'iso2': iso2,
            'tugo_country_name': country_name,
            'tugo_advisory_state': country.get('advisoryState'),
            'tugo_advisory_text': country.get('advisoryText'),
            'tugo_has_warning': int(bool(country.get('hasAdvisoryWarning'))),
            'tugo_has_regional': int(bool(country.get('hasRegionalAdvisory'))),
            'tugo_published_date': country.get('publishedDate'),
            'tugo_recent_updates': country.get('recentUpdates'),
            'tugo_advisories_desc': country.get('advisories', {}).get('description'),
        }
        summary_records.append(summary)

        # Extract climate info
        climate_info = country.get('climate', {}).get('climateInfo', [])
        for item in climate_info:
            climate_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'category': item.get('category'),
                'description': item.get('description')
            })

        # Extract health info
        health_info = country.get('health', {})

        # Diseases and vaccines
        diseases = health_info.get('diseasesAndVaccinesInfo', {})
        for disease_name, disease_info_list in diseases.items():
            for disease_info in disease_info_list:
                health_records.append({
                    'iso2': iso2,
                    'country_name': country_name,
                    'disease_name': disease_name,
                    'category': disease_info.get('category', ''),
                    'description': disease_info.get('description')
                })

        # General health info
        for item in health_info.get('healthInfo', []):
            health_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'disease_name': 'GENERAL',
                'category': item.get('category'),
                'description': item.get('description')
            })

        # Extract safety info
        safety_info = country.get('safety', {}).get('safetyInfo', [])
        for item in safety_info:
            safety_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'category': item.get('category'),
                'description': item.get('description')
            })

        # Extract law and culture info
        law_info = country.get('lawAndCulture', {}).get('lawAndCultureInfo', [])
        for item in law_info:
            laws_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'category': item.get('category'),
                'description': item.get('description')
            })

        # Extract entry/exit requirements
        entry_info = country.get('entryExitRequirement', {})
        for item in entry_info.get('requirementInfo', []):
            entry_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'category': item.get('category'),
                'description': item.get('description')
            })

        # Extract offices
        for office in country.get('offices', []):
            offices_records.append({
                'iso2': iso2,
                'country_name': country_name,
                'office_type': office.get('type'),
                'city': office.get('city'),
                'address': office.get('address'),
                'phone': office.get('phone'),
                'email': office.get('email1'),
                'website': office.get('website')
            })

    # Convert to DataFrames
    summary_df = pd.DataFrame(summary_records)

    # For summary: convert ISO2 to ISO3
    iso_map = load_iso_codes().reset_index()[['iso2', 'iso3']]
    summary_df = summary_df.merge(iso_map, on='iso2', how='left')
    summary_df = summary_df.drop(columns=['iso2'])
    summary_df = summary_df.set_index('iso3')

    # For detail tables: KEEP ISO2 (don't convert)
    climate_df = pd.DataFrame(climate_records)
    health_df = pd.DataFrame(health_records)
    safety_df = pd.DataFrame(safety_records)
    laws_df = pd.DataFrame(laws_records)
    entry_df = pd.DataFrame(entry_records)
    offices_df = pd.DataFrame(offices_records)

    # Print what was extracted
    print(f"  Extracted TuGo detail records:")
    print(f"    - Climate: {len(climate_df)}")
    print(f"    - Health: {len(health_df)}")
    print(f"    - Safety: {len(safety_df)}")
    print(f"    - Laws: {len(laws_df)}")
    print(f"    - Entry: {len(entry_df)}")
    print(f"    - Offices: {len(offices_df)}")

    detail_dfs = {
        'tugo_climate': climate_df,
        'tugo_health': health_df,
        'tugo_safety': safety_df,
        'tugo_laws': laws_df,
        'tugo_entry': entry_df,
        'tugo_offices': offices_df
    }

    return summary_df, detail_dfs


def load_foreign_office_travel_warnings():
    """Load German Foreign Office travel warning data."""
    try:
        filepath = get_data_path('foreign_office_travelwarnings.json')
    except FileNotFoundError:
        try:
            filepath = get_data_path('travelwarnings_snapshot.json')
        except FileNotFoundError:
            print("  ⚠️  Foreign Office travel warnings file not found, skipping...")
            return pd.DataFrame()

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.rename(columns={'iso3_country_code': 'iso3'})
    cols_to_drop = ['country_code', 'country_name']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])

    cols_to_prefix = [col for col in df.columns if col != 'iso3']
    df = df.rename(columns={col: f'fo_{col}' for col in cols_to_prefix})

    df = df.set_index('iso3')
    return df


def load_climate_data():
    """Load monthly climate data."""
    filepath = get_data_path('country_monthly_climate_2005_2024.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    countries_data = data['countries']
    climate_records = []

    for country_entry in countries_data:
        country_name = country_entry['country']
        months = country_entry.get('months', [])

        if not months:
            continue

        temps = [m['temp_c_clim'] for m in months if m.get('temp_c_clim') is not None]
        clouds = [m['cloud_pct'] for m in months if m.get('cloud_pct') is not None]
        precips = [m['precip_mm'] for m in months if m.get('precip_mm') is not None]

        record = {
            'country_name_climate': country_name,
            'climate_avg_temp_c': sum(temps) / len(temps) if temps else None,
            'climate_avg_cloud_pct': sum(clouds) / len(clouds) if clouds else None,
            'climate_total_precip_mm': sum(precips) if precips else None,
            'climate_avg_monthly_precip_mm': sum(precips) / len(precips) if precips else None,
        }

        for month_data in months:
            month_num = month_data['month']
            record[f'climate_temp_month_{month_num}'] = month_data.get('temp_c_clim')
            record[f'climate_cloud_month_{month_num}'] = month_data.get('cloud_pct')
            record[f'climate_precip_month_{month_num}'] = month_data.get('precip_mm')

        climate_records.append(record)

    df = pd.DataFrame(climate_records)
    return df

# Code for loading all Unesco sites into database
def load_unesco_heritage_data():
    """Load UNESCO World Heritage Sites data."""
    try:
        filepath = get_data_path('unesco_sites_full.json')
    except FileNotFoundError:
        print("  WARNING: UNESCO heritage sites file not found, skipping...")
        return pd.DataFrame()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  Found {len(data)} UNESCO heritage sites")
    df = pd.DataFrame(data)
    return df


def load_unesco_by_country_data():
    """Load summary UNESCO World Heritage Sites by country."""
    try:
        filepath = get_data_path('unesco_by_country.json')
    except FileNotFoundError:
        print("  WARNING: UNESCO by country file not found, skipping...")
        return pd.DataFrame()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"  Found {len(data)} UNESCO country summary records")
    df = pd.DataFrame(data)
    
    # Convert list columns to JSON strings for SQLite compatibility
    if 'site_names' in df.columns:
        df['site_names'] = df['site_names'].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    if 'site_ids' in df.columns:
        df['site_ids'] = df['site_ids'].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    
    return df

def load_numbeo_countries():
    """
    Load Numbeo country metadata: country_name, currency, iso3, country_param_used.
    We rename country_name to numbeo_country_name to avoid conflicts with the main country_name.
    """
    try:
        filepath = get_data_path('numbeo_countries.csv')
    except FileNotFoundError:
        print("  ⚠️ numbeo_countries.csv not found, skipping Numbeo country metadata...")
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    # Rename name and parameter columns to keep them clearly separated
    df = df.rename(columns={
        'country_name': 'numbeo_country_name',
        'country_param_used': 'numbeo_country_param_used'
    })

    if 'iso3' not in df.columns:
        print("  ⚠️ numbeo_countries.csv has no iso3 column, skipping...")
        return pd.DataFrame()

    df = df.set_index('iso3')
    return df


def load_numbeo_prices():
    """
    Load Numbeo country prices (large fact table).
    Will be stored as a separate table in SQLite (numbeo_prices).
    """
    try:
        filepath = get_data_path('numbeo_country_prices.csv')
    except FileNotFoundError:
        print("  ⚠️ numbeo_country_prices.csv not found, skipping Numbeo prices...")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    return df


def load_numbeo_exchange_rates():
    """
    Load Numbeo exchange rates.
    These live on the currency_code level, not per country.
    Will be stored as numbeo_exchange_rates.
    """
    try:
        filepath = get_data_path('numbeo_exchange_rates.csv')
    except FileNotFoundError:
        print("  ⚠️ numbeo_exchange_rates.csv not found, skipping Numbeo exchange rates...")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    # Optional: keep currency_code as index for convenience
    if 'currency_code' in df.columns:
        df = df.set_index('currency_code')
    return df


def load_numbeo_indices():
    """
    Load Numbeo country indices (cost of living, quality of life, etc.).
    We:
      - join via iso3
      - prefix most columns with 'numbeo_'
      - keep a separate table AND also join them into countries.
    """
    try:
        filepath = get_data_path('numbeo_country_indices.csv')
    except FileNotFoundError:
        print("  ⚠️ numbeo_country_indices.csv not found, skipping Numbeo indices...")
        return pd.DataFrame()

    df = pd.read_csv(filepath)

    if 'iso3' not in df.columns:
        print("  ⚠️ numbeo_country_indices.csv has no iso3 column, skipping...")
        return pd.DataFrame()

    # Avoid conflict with main country_name
    if 'country_name' in df.columns:
        df = df.rename(columns={'country_name': 'numbeo_country_name_indices'})

    # Prefix all metric columns with numbeo_
    rename_map = {}
    for col in df.columns:
        if col in ('iso3', 'numbeo_country_name_indices'):
            continue
        rename_map[col] = f"numbeo_{col}"

    df = df.rename(columns=rename_map)
    df = df.set_index('iso3')

    return df



def load_pictures_data():
    """
    Load Unsplash pictures. 
    If json missing, run the fetch script.
    Flattens the 3 images into separate columns.
    """
    filename = 'pictures.json'
    
    try:
        filepath = get_data_path(filename)
        print(f"  Loading pictures from: {filepath}")
    except FileNotFoundError:
        print("  ⚠️ pictures.json not found. Attempting to fetch from Unsplash...")
        try:
            from unsplash_api import fetch_country_images
            fetch_country_images()
            filepath = get_data_path(filename)
        except Exception as e:
            print(f"  ❌ Error fetching images: {e}")
            return pd.DataFrame()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return pd.DataFrame()

        # Flatten the nested JSON into a flat dictionary for DataFrame
        flattened_records = []
        for entry in data:
            record = {'iso3': entry['iso3']}
            
            # Extract up to 3 images
            images = entry.get('images', [])
            for i in range(3): # 0, 1, 2
                if i < len(images):
                    # Columns: img_1, credit_1, img_2, credit_2, ...
                    suffix = str(i + 1)
                    img = images[i]
                    record[f'img_{suffix}'] = img.get('image_url')
                    record[f'credit_{suffix}'] = img.get('photographer_name')
                    record[f'credit_url_{suffix}'] = img.get('photographer_url')
                else:
                    # Fill empty if less than 3 images found
                    suffix = str(i + 1)
                    record[f'img_{suffix}'] = None
                    record[f'credit_{suffix}'] = None
                    record[f'credit_url_{suffix}'] = None
            
            flattened_records.append(record)

        df = pd.DataFrame(flattened_records)
        df = df.set_index('iso3')
        return df
        
    except Exception as e:
        print(f"  ❌ Error reading pictures.json: {e}")
        return pd.DataFrame()

def load_airports_data():
    """
    Load Airport data using the amadeus_api script.
    """
    try:
        # Assumes amadeus_api.py is in the same directory
        from amadeus_api import load_airport_data
        return load_airport_data()
    except ImportError:
        print("  ⚠️ amadeus_api.py not found. Skipping airports.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  ❌ Error loading airports: {e}")
        return pd.DataFrame()

def load_flight_network_data(airports_df):
    """
    Load Flight Cost data. Relies on airports_df to determine routes.
    """
    if airports_df.empty:
        print("  ⚠️ No airport data available. Skipping flight network.")
        return pd.DataFrame()

    try:
        from fetch_route_prices import get_flight_network_data
        return get_flight_network_data(airports_df)
    except ImportError:
        print("  ⚠️ fetch_route_prices.py not found. Skipping flight network.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  ❌ Error loading flight network: {e}")
        return pd.DataFrame()

def create_unified_database(output_db='unified_country_database.db'):
    """Create a unified database from all data sources."""

    print("\n" + "="*60)
    print("UNIFIED COUNTRY DATABASE CREATOR - FIXED")
    print("="*60)
    print("\nLoading data sources...")

    print("  - ISO country codes (base table)")
    iso_df = load_iso_codes()

    print("  - PLI (Price Level Index) data")
    pli_df = load_pli_data()

    print("  - Exchange rate data")
    exchange_df = load_exchange_data()

    print("  - TuGo travel warnings with DETAILS")
    tugo_summary_df, tugo_detail_dfs = load_tugo_travel_warnings_with_details()

    print("  - Foreign Office travel warnings")
    fo_df = load_foreign_office_travel_warnings()

    print("  - Climate data")
    climate_df = load_climate_data()

    print("  - UNESCO World Heritage Sites")
    unesco_df = load_unesco_heritage_data()

    # 🔹 Numbeo data (countries, prices, exchange rates, indices)
    print("  - Numbeo countries / prices / exchange rates / indices")
    numbeo_countries_df = load_numbeo_countries()
    numbeo_prices_df = load_numbeo_prices()
    numbeo_exchange_df = load_numbeo_exchange_rates()
    numbeo_indices_df = load_numbeo_indices()


    print("  - UNESCO by country summary")
    unesco_by_country_df = load_unesco_by_country_data()

    print("  - Unsplash Country Pictures")
    pictures_df = load_pictures_data()

    print("  - Airports Data (OpenTravelData + Rankings)")
    airports_df = load_airports_data()

    print("  - Flight Network (Prices from US/DE)")
    # We pass the airports_df we just loaded so the script knows the top airports
    flight_costs_df = load_flight_network_data(airports_df)

    print("\nMerging datasets on ISO3 country codes...")

    unified_df = iso_df.copy()
    unified_df = unified_df.join(pli_df, how='left')
    unified_df = unified_df.join(exchange_df, how='left')

    if not tugo_summary_df.empty:
        unified_df = unified_df.join(tugo_summary_df, how='left')

    if not fo_df.empty:
        unified_df = unified_df.join(fo_df, how='left')

    if not pictures_df.empty:
        unified_df = unified_df.join(pictures_df, how='left')

# 🔹 Numbeo: country metadata (currency, numbeo_country_name, etc.)
    if not numbeo_countries_df.empty:
        unified_df = unified_df.join(numbeo_countries_df, how='left')

    # 🔹 Numbeo: indices (cost of living, quality of life, etc.)
    if not numbeo_indices_df.empty:
        unified_df = unified_df.join(numbeo_indices_df, how='left')

    unified_df = unified_df.reset_index()

    print(f"✓ Unified dataset: {len(unified_df)} countries × {len(unified_df.columns)} columns")

    # Save to database
    script_dir = Path(__file__).parent
    db_path = script_dir / output_db

    print(f"\nSaving to SQLite: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Save main table
    unified_df.to_sql('countries', conn, if_exists='replace', index=False)
    print(f"  ✓ 'countries' table: {len(unified_df)} rows")

    # Save climate table
    climate_df.to_sql('climate_monthly', conn, if_exists='replace', index=False)
    print(f"  ✓ 'climate_monthly' table: {len(climate_df)} rows")

    # Save UNESCO heritage sites table
    if not unesco_df.empty:
        unesco_df.to_sql('unesco_heritage_sites', conn, if_exists='replace', index=False)
        print(f"  * 'unesco_heritage_sites' table: {len(unesco_df)} rows")
    else:
        print("  * 'unesco_heritage_sites' table skipped (no data)")

    # Save UNESCO summary by country table
    if not unesco_by_country_df.empty:
        unesco_by_country_df.to_sql('unesco_by_country', conn, if_exists='replace', index=False)
        print(f"  * 'unesco_by_country' table: {len(unesco_by_country_df)} rows")
    else:
        print("  * 'unesco_by_country' table skipped (no data)")

    # Save Airports table
    if not airports_df.empty:
        airports_df.to_sql('airports', conn, if_exists='replace', index=False)
        print(f"  ✓ 'airports' table: {len(airports_df)} rows")
    else:
        print("  ⚠️ 'airports' table skipped (no data)")

    # Save Flight Costs table
    if not flight_costs_df.empty:
        flight_costs_df.to_sql('flight_costs', conn, if_exists='replace', index=False)
        print(f"  ✓ 'flight_costs' table: {len(flight_costs_df)} rows")
    else:
        print("  ⚠️ 'flight_costs' table skipped (no data)")

    # 🔹 Save Numbeo prices table
    if not numbeo_prices_df.empty:
        numbeo_prices_df.to_sql('numbeo_prices', conn, if_exists='replace', index=False)
        print(f"  ✓ 'numbeo_prices' table: {len(numbeo_prices_df)} rows")
    else:
        print("  ⚠️ 'numbeo_prices' table skipped (no data)")

    # 🔹 Save Numbeo exchange rates table
    if not numbeo_exchange_df.empty:
        numbeo_exchange_df.reset_index().to_sql('numbeo_exchange_rates', conn, if_exists='replace', index=False)
        print(f"  ✓ 'numbeo_exchange_rates' table: {len(numbeo_exchange_df)} rows")
    else:
        print("  ⚠️ 'numbeo_exchange_rates' table skipped (no data)")

    # 🔹 Save Numbeo indices as a separate table as well
    if not numbeo_indices_df.empty:
        numbeo_indices_df.reset_index().to_sql('numbeo_indices', conn, if_exists='replace', index=False)
        print(f"  ✓ 'numbeo_indices' table: {len(numbeo_indices_df)} rows")
    else:
        print("  ⚠️ 'numbeo_indices' table skipped (no data)")

    # CRITICAL: Save TuGo detail tables
    if tugo_detail_dfs:
        for table_name, df in tugo_detail_dfs.items():
            if not df.empty:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                print(f"  ✓ '{table_name}' table: {len(df)} rows")

    # Create indexes
    cursor = conn.cursor()
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_countries_iso3 ON countries(iso3)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_climate_country ON climate_monthly(country_name_climate)')

    # Indexes for detail tables
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_climate_iso2 ON tugo_climate(iso2)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_health_iso2 ON tugo_health(iso2)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_safety_iso2 ON tugo_safety(iso2)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_laws_iso2 ON tugo_laws(iso2)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_entry_iso2 ON tugo_entry(iso2)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tugo_offices_iso2 ON tugo_offices(iso2)')

    # Indexes for UNESCO tables
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unesco_country_iso ON unesco_heritage_sites(country_iso)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unesco_id ON unesco_heritage_sites(id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unesco_by_country_iso_code ON unesco_by_country(iso_code)')

    # Indexes for Airports
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports(iata_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_airports_iso2 ON airports(iso2)')
    
    # Indexes for Numbeo tables
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_numbeo_prices_iso3 ON numbeo_prices(iso3)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_numbeo_prices_item ON numbeo_prices(item_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_numbeo_exrates_currency ON numbeo_exchange_rates(currency_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_numbeo_indices_iso3 ON numbeo_indices(iso3)')

    # Indexes for Flight Costs
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flights_origin ON flight_costs(origin)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flights_dest ON flight_costs(destination)')

    conn.commit()
    print(f"  ✓ Indexes created")

    # Summary
    print("\n" + "="*60)
    print("DATABASE CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"\nDatabase file: {db_path}")
    print(f"\nTables created:")
    print(f"  - countries ({len(unified_df)} rows)")
    print(f"  - climate_monthly ({len(climate_df)} rows)")
    print(f"  - unesco_heritage_sites ({len(unesco_df)} rows)")
    print(f"  - unesco_by_country ({len(unesco_by_country_df)} rows)")
    if not airports_df.empty:
        print(f"  - airports ({len(airports_df)} rows)")
    if not flight_costs_df.empty:
        print(f"  - flight_costs ({len(flight_costs_df)} rows)")
    if tugo_detail_dfs:
        for table_name, df in tugo_detail_dfs.items():
            if not df.empty:
                print(f"  - {table_name} ({len(df)} rows)")

    print(f"\nQUERY EXAMPLES:")
    print(f"  # Get all health info for Afghanistan:")
    print(f"  SELECT * FROM tugo_health WHERE iso2 = 'AF';")
    print(f"\n  # Get all safety warnings for high-risk countries:")
    print(f"  SELECT DISTINCT iso2 FROM tugo_safety WHERE description LIKE '%terrorist%';")
    print(f"\n  # Get climate risks by category:")
    print(f"  SELECT iso2, category, COUNT(*) FROM tugo_climate GROUP BY iso2, category;")
    print("\n" + "="*60)

    conn.close()

    return unified_df, climate_df


if __name__ == '__main__':
    create_unified_database()
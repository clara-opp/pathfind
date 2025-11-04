import pandas as pd
import os
import sqlite3

def fetch_and_process_airport_data():
    """
    Fetches the latest airport data from OpenTravelData, processes it,
    and saves it to a CSV file.
    """
    url = 'https://raw.githubusercontent.com/opentraveldata/opentraveldata/master/opentraveldata/optd_por_public.csv'

    # Define the columns you are interested in to save memory
    columns_to_use = [
        'iata_code',
        'name',
        'city_name_list',
        'country_name',      # Added
        'country_code',      # Added (will be renamed to 'country')
        'latitude',
        'longitude',
        'timezone',
        'page_rank',          # Added
        'fcode'
    ]

    print("Starting data download...")
    try:
        # OpenTravelData uses '^' as a separator in their CSV
        df = pd.read_csv(url, sep='^', usecols=columns_to_use, low_memory=False)
        print("Data downloaded successfully.")

        # --- Data Cleaning and Processing ---

        # 1. Filter for valid airports
        df_airports = df[df['iata_code'].str.match(r'^[A-Z]{3}$', na=False)].copy()

        # 2. Filter out heliports, etc., keeping only major airports
        df_airports = df_airports[df_airports['fcode'] == 'AIRP'].copy()
        
        # 3. Drop rows with missing essential data
        df_airports.dropna(subset=['timezone', 'city_name_list', 'country_name'], inplace=True)
        
        # 4 Clean up city names (e.g., "Dallas=Fort Worth" -> "Dallas")
        df_airports.rename(columns={
            'city_name_list': 'city',
            'country_code': 'country'
        }, inplace=True)

        df_airports['city'] = df_airports['city'].str.split('=').str[0]

        # 5. Set a proper index
        df_airports.set_index('iata_code', inplace=True)
        
        # 6. Sort by page_rank to see the most important airports at the top
        df_airports.sort_values(by='page_rank', ascending=False, inplace=True)

        # --- Saving the Data ---
        output_filename = 'airports.db'
        table_name = 'airports'
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.getcwd()
            
        output_path = os.path.join(script_dir, output_filename)

        # Connect to SQLite database (this will create the file if it doesn't exist)
        conn = sqlite3.connect(output_path)
        
        # Write the dataframe to a table, replacing it if it already exists
        # The iata_code index will be saved as a column named 'iata_code'
        df_airports.to_sql(table_name, conn, if_exists='replace', index=True)
        
        conn.close()

        print(f"Processing complete. Data saved to table '{table_name}' in {output_path}")
        print(f"Total airports processed: {len(df_airports)}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    fetch_and_process_airport_data()
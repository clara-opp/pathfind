#!/usr/bin/env python3
"""
tugo_api.py — Fetch TuGo travel warnings for all countries
Saves to data/tugo_travelwarnings.json
"""

import os
import requests
import json
import time
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("tugo_api")
if not API_KEY:
    raise ValueError("tugo_api environment variable not set! Add it to your .env file")

BASE_URL = "https://api.tugo.com/v1/travelsafe/countries"

# Save to data subfolder (script is in database/, saves to database/data/)
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "tugo_travelwarnings.json"

# ISO2 country codes (216 successful countries)
COUNTRY_CODES = [
    'AF', 'AL', 'DZ', 'AS', 'AD', 'AO', 'AI', 'AQ', 'AG', 'AR', 'AM', 'AW', 
    'AU', 'AT', 'AZ', 'BS', 'BH', 'BD', 'BB', 'BE', 'BZ', 'BJ', 'BM', 'BT', 
    'BO', 'BQ', 'BA', 'BW', 'BR', 'BN', 'BG', 'BF', 'BI', 'KH', 'CM', 
    'CV', 'KY', 'CF', 'TD', 'CL', 'CN', 'KM', 'CG', 'CD', 
    'CK', 'CR', 'HR', 'CU', 'CW', 'CY', 'DK', 'DJ', 'DM', 'DO', 'EC', 
    'EG', 'SV', 'GQ', 'EE', 'ET', 'FK', 'FJ', 'FI', 'FR', 'GF', 'PF', 
    'GA', 'GM', 'GE', 'DE', 'GH', 'GI', 'GR', 'GL', 'GD', 'GP', 'GU', 'GT', 
    'GN', 'GW', 'GY', 'HN', 'HK', 'HU', 'IS', 'IN', 'ID', 
    'IR', 'IQ', 'IE', 'IL', 'IT', 'JM', 'JP', 'JO', 'KZ', 'KE', 'KI', 
    'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 'LB', 'LS', 'LR', 'LY', 'LI', 'LT', 'LU', 
    'MO', 'MK', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MQ', 'MR', 'MU', 'YT', 
    'MX', 'FM', 'MC', 'MN', 'ME', 'MS', 'MA', 'MZ', 'MM', 'NA', 'NR', 'NP', 
    'NL', 'NC', 'NZ', 'NI', 'NE', 'NG', 'NU', 'MP', 'NO', 'OM', 'PK', 'PW', 
    'PA', 'PG', 'PY', 'PH', 'PL', 'PT', 'PR', 'QA', 'RO', 
    'RU', 'RW', 'BL', 'KN', 'LC', 'MF', 'PM', 'VC', 'WS', 'SM', 'ST', 'SA', 
    'SN', 'RS', 'SC', 'SL', 'SG', 'SX', 'SK', 'SI', 'SB', 'SO', 'ZA', 'SS', 
    'ES', 'LK', 'SR', 'SZ', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 'TH', 
    'TL', 'TG', 'TK', 'TO', 'TT', 'TN', 'TR', 'TM', 'TC', 'TV', 'UG', 'UA', 'AE', 
    'GB', 'US', 'UY', 'UZ', 'VU', 'VE', 'VN', 'VG', 'VI', 'ZM', 'ZW'
]


def fetch_country(country_code):
    """Fetch travel warning data for a single country."""
    headers = {
        'Accept': 'application/json',
        'X-Auth-API-Key': API_KEY
    }

    try:
        url = f"{BASE_URL}/{country_code}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"  FAIL: Error fetching {country_code}: {e}")
        return None


def main():
    """Fetch all countries and save to JSON file."""
    print("="*60)
    print("Fetching TuGo travel warnings...")
    print(f"Output: {OUTPUT_FILE}")
    print("="*60)

    all_data = []
    successful = 0
    failed = 0

    for i, code in enumerate(COUNTRY_CODES, 1):
        # Progress indicator
        print(f"[{i:3d}/{len(COUNTRY_CODES)}] {code}...", end=' ', flush=True)

        data = fetch_country(code)

        if data:
            all_data.append(data)
            successful += 1
            print("OK")
        else:
            failed += 1
            print("FAILED")

        # Rate limiting - be nice to the API
        time.sleep(0.1)

    # Save combined file
    print("\n" + "="*60)
    print("Saving data...")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "="*60)
    print("COMPLETE!")
    print("="*60)
    print(f"Total countries: {len(COUNTRY_CODES)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    print("="*60)


if __name__ == '__main__':
    main()
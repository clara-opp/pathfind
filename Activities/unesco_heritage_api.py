import requests
import pandas as pd
import json
import time
import os

def fetch_unesco_api_data(limit=100, offset=0):
    """
    Fetch data from UNESCO Open Data API v2.1
    """
    base_url = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/records"
    
    params = {
        'limit': limit,
        'offset': offset
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def fetch_all_unesco_sites():
    """
    Fetch all UNESCO World Heritage Sites
    """
    print("Fetching UNESCO World Heritage Sites...")
    print("-" * 70)
    
    all_results = []
    limit = 100
    offset = 0
    
    while True:
        print(f"\nBatch: offset={offset}, limit={limit}")
        
        data = fetch_unesco_api_data(limit=limit, offset=offset)
        
        if not data or 'results' not in data:
            print("  No data received")
            break
        
        results = data['results']
        
        if not results:
            print("  No more results")
            break
        
        all_results.extend(results)
        
        total_count = data.get('total_count', 0)
        print(f"  Progress: {len(all_results)}/{total_count}")
        
        if len(all_results) >= total_count:
            break
        
        offset += limit
        time.sleep(0.3)
    
    print(f"\nFetched {len(all_results)} total records")
    return all_results

def process_unesco_data(raw_data):
    """
    Process UNESCO API data with correct field names
    """
    print("\nProcessing data...")
    print("-" * 70)
    
    if not raw_data:
        return []
    
    processed_sites = []
    
    for i, record in enumerate(raw_data):
        try:
            site = {
                'id': record.get('id_no', ''),
                'name': record.get('name_en', ''),
                'name_fr': record.get('name_fr', ''),
                'name_es': record.get('name_es', ''),
                'country': ', '.join(record.get('states_names', [])),
                'country_iso': record.get('iso_codes', ''),
                'region': record.get('region', ''),
                'category': record.get('category', ''),
                'short_description': record.get('short_description_en', ''),
                'description': record.get('description_en', ''),
                'justification': record.get('justification_en', ''),
                'date_inscribed': record.get('date_inscribed', ''),
                'secondary_dates': record.get('secondary_dates', ''),
                'danger': record.get('danger', 'False'),
                'danger_list': True if record.get('danger') == 'True' else False,
                'area_hectares': record.get('area_hectares', 0),
                'criteria_txt': record.get('criteria_txt', ''),
                'cultural_criteria': record.get('cultural_criteria', ''),
                'natural_criteria': record.get('natural_criteria', ''),
                'transboundary': record.get('transboundary', 'False'),
                'components_count': record.get('components_count', 0),
                'longitude': record.get('coordinates', {}).get('lon') if record.get('coordinates') else None,
                'latitude': record.get('coordinates', {}).get('lat') if record.get('coordinates') else None,
                'main_image_url': record.get('main_image_url', {}).get('url', '') if record.get('main_image_url') else '',
                'images_urls': record.get('images_urls', '')
            }
            
            processed_sites.append(site)
            
            if i < 3:
                print(f"  Sample {i+1}: {site['name']} ({site['country']}) - {site['category']}")
        
        except Exception as e:
            print(f"  ERROR processing record {i}: {e}")
            continue
    
    print(f"\nProcessed {len(processed_sites)} sites")
    return processed_sites

def aggregate_by_country(sites):
    """
    Aggregate by country with category breakdown
    """
    from collections import defaultdict
    
    print("\nAggregating by country...")
    print("-" * 70)
    
    country_stats = defaultdict(lambda: {
        'country_name': '',
        'iso_code': '',
        'region': '',
        'total_sites': 0,
        'cultural_sites': 0,
        'natural_sites': 0,
        'mixed_sites': 0,
        'danger_sites': 0,
        'transboundary_sites': 0,
        'site_names': [],
        'site_ids': []
    })
    
    for site in sites:
        countries = site['country'].split(', ')
        iso_codes = site['country_iso'].split(', ') if site['country_iso'] else []
        
        for idx, country in enumerate(countries):
            if not country:
                continue
            
            iso_code = iso_codes[idx] if idx < len(iso_codes) else ''
            
            country_stats[country]['country_name'] = country
            country_stats[country]['iso_code'] = iso_code
            country_stats[country]['region'] = site['region']
            country_stats[country]['total_sites'] += 1
            country_stats[country]['site_names'].append(site['name'])
            country_stats[country]['site_ids'].append(site['id'])
            
            category = site['category']
            if category == 'Cultural':
                country_stats[country]['cultural_sites'] += 1
            elif category == 'Natural':
                country_stats[country]['natural_sites'] += 1
            elif category == 'Mixed':
                country_stats[country]['mixed_sites'] += 1
            
            if site['danger_list']:
                country_stats[country]['danger_sites'] += 1
            
            if site['transboundary'] == 'True':
                country_stats[country]['transboundary_sites'] += 1
    
    result = sorted(country_stats.values(), key=lambda x: x['total_sites'], reverse=True)
    print(f"Aggregated {len(result)} countries")
    return result

def save_data(sites, country_stats):
    """
    Save to JSON and CSV
    """
    print("\nSaving files...")
    print("-" * 70)
    
    current_dir = os.getcwd()
    
    with open('unesco_sites_full.json', 'w', encoding='utf-8') as f:
        json.dump(sites, f, indent=2, ensure_ascii=False)
    size = os.path.getsize('unesco_sites_full.json')
    print(f"  unesco_sites_full.json ({size:,} bytes)")
    
    with open('unesco_by_country.json', 'w', encoding='utf-8') as f:
        json.dump(country_stats, f, indent=2, ensure_ascii=False)
    size = os.path.getsize('unesco_by_country.json')
    print(f"  unesco_by_country.json ({size:,} bytes)")
    
    df_sites = pd.DataFrame(sites)
    df_sites.to_csv('unesco_sites_full.csv', index=False, encoding='utf-8')
    print(f"  unesco_sites_full.csv ({len(df_sites)} rows)")
    
    df_countries = pd.DataFrame(country_stats)
    df_countries.to_csv('unesco_by_country.csv', index=False, encoding='utf-8')
    print(f"  unesco_by_country.csv ({len(df_countries)} rows)")

def print_summary(sites, country_stats):
    """
    Print summary with category breakdown
    """
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    
    print(f"\nTotal Sites: {len(sites)}")
    print(f"Total Countries: {len(country_stats)}")
    
    cultural = sum(1 for s in sites if s['category'] == 'Cultural')
    natural = sum(1 for s in sites if s['category'] == 'Natural')
    mixed = sum(1 for s in sites if s['category'] == 'Mixed')
    danger = sum(1 for s in sites if s['danger_list'])
    
    print(f"\nBy Category:")
    print(f"  Cultural: {cultural}")
    print(f"  Natural: {natural}")
    print(f"  Mixed: {mixed}")
    print(f"\nSites in Danger: {danger}")
    
    if country_stats:
        print(f"\nTop 20 Countries:")
        print("-" * 90)
        print(f"{'Rank':<5} {'Country':<25} {'ISO':<5} {'Total':<7} {'Cultural':<10} {'Natural':<9} {'Mixed':<7} {'Danger':<7}")
        print("-" * 90)
        
        for i, country in enumerate(country_stats[:20], 1):
            print(f"{i:<5} {country['country_name']:<25} {country['iso_code']:<5} "
                  f"{country['total_sites']:<7} {country['cultural_sites']:<10} "
                  f"{country['natural_sites']:<9} {country['mixed_sites']:<7} "
                  f"{country['danger_sites']:<7}")

def main():
    print("=" * 90)
    print("UNESCO WORLD HERITAGE SITES DATA COLLECTOR")
    print("=" * 90)
    
    raw_data = fetch_all_unesco_sites()
    
    if not raw_data:
        print("\nERROR: No data fetched")
        return
    
    sites = process_unesco_data(raw_data)
    
    if not sites:
        print("\nERROR: No sites processed")
        return
    
    country_stats = aggregate_by_country(sites)
    
    save_data(sites, country_stats)
    
    print_summary(sites, country_stats)
    
    print("\n" + "=" * 90)
    print("COMPLETE")
    print("=" * 90)

if __name__ == "__main__":
    main()

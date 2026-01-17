import os
import json
import requests
from dotenv import load_dotenv

def test_serper_price_search(query: str):
    """
    Simulates the price search tool to see what raw data comes back.
    """
    load_dotenv()
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    
    if not api_key:
        print("❌ ERROR: Missing SERPER_API_KEY in your .env file.")
        return

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {"q": query}

    print(f"\n--- Searching for: '{query}' ---")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        res_data = response.json()

        # 1. Check for an "Answer Box" (Google's direct answer)
        if "answerBox" in res_data:
            print("\n✅ GOOGLE ANSWER BOX FOUND:")
            print(json.dumps(res_data["answerBox"], indent=2))

        # 2. Check "Organic" results (The snippets the AI reads)
        print("\n🌐 TOP 3 ORGANIC SNIPPETS:")
        organic = res_data.get("organic", [])
        for i, result in enumerate(organic[:3]):
            print(f"\n[{i+1}] Title: {result.get('title')}")
            print(f"    Snippet: {result.get('snippet')}")
            print(f"    Link: {result.get('link')}")

        # 3. Print the full raw JSON structure (commented out by default to avoid clutter)
        # print("\nRAW JSON RESPONSE:")
        # print(json.dumps(res_data, indent=2))

    except Exception as e:
        print(f"❌ API CALL FAILED: {str(e)}")

if __name__ == "__main__":
    # Test cases relevant to your Trip Planner
    test_queries = [
        "Louvre Museum entrance fee 2024 2025",
        "average price of a main course at Borchardt restaurant Berlin",
        "Berlin TV Tower ticket price 2025",
        "cost of a cup of coffee in Munich city center"
    ]

    print("SERPER API TEST TOOL")
    print("===================")
    
    for q in test_queries:
        test_serper_price_search(q)
        input("\nPress Enter to run next test query...")
    
    print("\nTests complete.")
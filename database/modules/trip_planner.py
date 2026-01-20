import os
import json
import unicodedata
import requests
import math
import time
import sqlite3
import streamlit as st
import streamlit.components.v1 as components
import concurrent.futures
from geopy.geocoders import Nominatim
import pycountry
import geonamescache
import folium
from streamlit_folium import st_folium
from folium.plugins import BeautifyIcon, Fullscreen, MeasureControl
from dotenv import load_dotenv
from openai import OpenAI
import polyline

# ---------- Google Places API client ----------
@st.cache_data(show_spinner=False)
def google_search_places(query: str, ll: str, radius: int = 4000, limit: int = 8):
    """
    Search for places using Google Places API (New).
    ll: "lat,lon" string, e.g. "49.75,8.65"
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY")
    
    url = "https://places.googleapis.com/v1/places:searchText"
    
    # Parse lat/lon
    lat_str, lon_str = ll.split(",")
    lat, lon = float(lat_str), float(lon_str)
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri,places.nationalPhoneNumber,places.photos"
    }
    
    data = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": radius
            }
        },
        "maxResultCount": limit
    }
    
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        
        if r.status_code != 200:
            print(f"GOOGLE ERROR: {r.status_code} - {r.text}")
            return {"error": True, "status": r.status_code, "body": r.text}
        
        response_data = r.json()
        results = []
        
        print(f"DEBUG GOOGLE SEARCH: Query='{query}' | Limit={limit}")

        for p in response_data.get("places", []):
            # Construct photo URLs (up to 3)
            photo_urls = []            
            if p.get("photos"):
                for photo in p["photos"][:3]:
                    photo_name = photo.get("name")
                    url = f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxWidthPx=400"
                    photo_urls.append(url)

            # Extract location coordinates
            location = p.get("location", {})
            place_lat = location.get("latitude")
            place_lon = location.get("longitude")
            
            # Calculate distance (approximate)
            distance_m = None
            if place_lat and place_lon:
                import math
                # Haversine formula for approximate distance
                dlat = math.radians(place_lat - lat)
                dlon = math.radians(place_lon - lon)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(place_lat)) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance_m = 6371000 * c  # Earth radius in meters
            
            results.append({
                "place_id": p.get("id", ""),
                "name": p.get("displayName", {}).get("text", ""),
                "distance_m": distance_m,
                "categories": p.get("types", []),
                "address": p.get("formattedAddress", ""),
                "website": p.get("websiteUri", ""),
                "tel": p.get("nationalPhoneNumber", ""),
                "photo_urls": photo_urls,
                "latitude": place_lat,
                "longitude": place_lon,
            })
        
        print(f"DEBUG GOOGLE RESULTS: Found {len(results)} places:")
        for i, res in enumerate(results, 1):
            print(f"  {i}. {res['name']} (ID: {res['place_id']})")

        return {"error": False, "results": results}
    
    except Exception as e:
        return {"error": True, "message": str(e)}


# ---------- Helper: Google Routes API ----------
@st.cache_data(show_spinner=False)
def get_route_google(coordinates, api_key, optimize=False):
    """
    Get walking route using Google Routes API.
    coordinates: List of [lat, lon] pairs.
    Returns: {"polyline": [[lat, lon], ...], "optimized_indices": [int, ...]}
    """
    if len(coordinates) < 2:
        return {"polyline": [], "optimized_indices": []}
    
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.optimizedIntermediateWaypointIndex"
    }
    
    # Build waypoints
    waypoints = []
    for i, coord in enumerate(coordinates):
        waypoint = {
            "location": {
                "latLng": {
                    "latitude": coord[0],
                    "longitude": coord[1]
                }
            }
        }
        if i == 0:
            origin = waypoint
        elif i == len(coordinates) - 1:
            destination = waypoint
        else:
            waypoints.append({"via": False, **waypoint})
    
    data = {
        "origin": origin,
        "destination": destination,
        "polylineQuality": "HIGH_QUALITY",
        "optimizeWaypointOrder": "true" if optimize and len(waypoints) > 0 else "false"
    }
    
    if waypoints:
        data["intermediates"] = waypoints
    
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"DEBUG: Google Routes API Status: {r.status_code}")
        if r.status_code == 200:
            response_data = r.json()
            routes = response_data.get("routes", [])
            print(f"DEBUG: Google Routes found: {len(routes)} routes")
            if routes:
                route = routes[0]
                encoded = route.get("polyline", {}).get("encodedPolyline", "")
                # Google returns the new indices for intermediates only
                opt_indices = route.get("optimizedIntermediateWaypointIndex", [])
                
                return {
                    "polyline": polyline.decode(encoded) if encoded else [],
                    "optimized_indices": opt_indices
                }
    except Exception as e:
        print(f"DEBUG: Google Routes Exception: {str(e)}")
    
    return {"polyline": [], "optimized_indices": []}

@st.cache_data(show_spinner=False)
def get_deterministic_durations(origin_ll, dest_ll):
    """Fetch real durations for Foot, Car, and Transit between two points."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    modes = {"WALK": "travel_foot", "DRIVE": "travel_car", "TRANSIT": "travel_transit"}
    results = {"travel_foot": "-", "travel_car": "-", "travel_transit": "-"}
    
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": "routes.duration"}

    for google_mode, ui_key in modes.items():
        data = {
            "origin": {"location": {"latLng": {"latitude": origin_ll[0], "longitude": origin_ll[1]}}},
            "destination": {"location": {"latLng": {"latitude": dest_ll[0], "longitude": dest_ll[1]}}},
            "travelMode": google_mode
        }
        try:
            r = requests.post(url, headers=headers, json=data, timeout=5)
            if r.status_code == 200:
                resp_json = r.json()
                if 'routes' in resp_json and len(resp_json['routes']) > 0:
                    duration_sec = int(resp_json['routes'][0]['duration'].replace('s', ''))
                    duration_min = round(duration_sec / 60)
                    print(f"DEBUG TRAVEL API: Mode={google_mode} | Result={duration_min} min")
                    results[ui_key] = f"{duration_min} min"
                else:
                    print(f"DEBUG TRAVEL API: Mode={google_mode} | Status=OK but NO ROUTES FOUND (Common in restricted regions like Russia)")
            else:
                print(f"DEBUG TRAVEL API: Mode={google_mode} | Error={r.status_code} - {r.text}")
        except:
            continue
    return results

# ---------- Fallback: OSRM Routing ----------
@st.cache_data(show_spinner=False)
def get_route_osrm(coordinates):
    """
    Fallback routing using free OSRM service.
    coordinates: List of [lat, lon] pairs.
    Returns: List of [lat, lon] points representing the walking path.
    """
    locs = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
    url = f"http://router.project-osrm.org/route/v1/foot/{locs}?overview=full&geometries=polyline"
    
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                encoded = data["routes"][0]["geometry"]
                return polyline.decode(encoded)
    except Exception:
        pass
    
    return []

@st.cache_data(show_spinner=False)
def serper_search_prices(query: str, num_results: int = 6):
    """Search the web for current prices, entrance fees, or menu costs."""
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        return {"error": "Missing SERPER_API_KEY"}
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json={"q": query, "num": num_results}, timeout=15) 
        res = r.json()
        print(f"DEBUG: Serper API returned {len(res.get('organic', []))} results for: {query}")
        return res
    except Exception as e:
        return {"error": str(e)}


# ---------- OpenAI tool-calling loop ----------
def run_planner(messages, ll: str, radius: int, budget_val: float, persona: str, currency: str, city: str, iso3: str):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        max_retries=5
    )
    found_places = []

    # 1. Start Currency Lookup immediately (Parallel to Phase 1)
    def get_conversion():
        try:
            # Fix: Find database in the parent directory relative to this module
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "..", "unified_country_database.db")
            
            # Fallback for different execution contexts
            if not os.path.exists(db_path):
                db_path = os.path.join(base_dir, "unified_country_database.db")

            print(f"DEBUG DB: Connecting to {db_path} for ISO3='{iso3}'")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.one_eur_to_currency, r.currency 
                    FROM numbeo_exchange_rates r
                    WHERE r.currency = (SELECT currency FROM numbeo_prices WHERE iso3 = ? LIMIT 1)""", (iso3,))
                res = cursor.fetchone()
                if res:
                    print(f"DEBUG DB: Success! Rate={res[0]}, Currency={res[1]}")
                    return res
                return (1.0, "Unknown")
        except Exception as e:
            print(f"DEBUG DB ERROR: {e}")
            return (1.0, "Unknown")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        db_future = executor.submit(get_conversion)
    
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "google_search_places",
                    "description": "Search for places near a lat/lon using Google Places API.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search term, e.g. 'museum', 'cafe', 'park'."},
                            "ll": {"type": "string", "description": "Lat,lon string, e.g. '49.75,8.65'."},
                            "radius": {"type": "integer", "description": "Radius in meters."},
                            "limit": {"type": "integer", "description": "Max number of results."},
                        },
                        "required": ["query", "ll"],
                    },
                },
            },
        ]
    
        system_msg = {
            "role": "system",
            "content": (
                "You are a day-trip planner.\n"
                "Goal: propose a realistic day-trip itinerary within the user's fixed budget.\n"
                "Rules:\n"
                "- Use google_search_places to fetch real nearby places. You MUST generate ALL search queries for the entire day if not specified otherwise by the user.\n"
                "- Once you have searched for places, the system will automatically provide real-world price data for them. Use that data for your budget calculations.\n"
                "- Target spending: Aim for a total cost between 85% and 90% of the budget. Never exceed the budget. Do NOT mention these percentages or internal budget rules to the user.\n"
                "- Use the provided price data for every activity. Do not include disclaimers like 'could not be retrieved'; use the data provided or your best estimate if data is missing.\n"
                "- IMPORTANT: Disregard all previous locations or search results if the search center (ll) has changed. Only use places found in the CURRENT tool calls.\n"
                "- ID MATCHING: You MUST use the exact 'place_id' string from the CURRENT tool output. NEVER reuse IDs from previous turns. If you cannot find an ID, use the 'name' of the place as the ID.\n"
                "- Return a JSON object with four keys: 'assistant_message', 'itinerary', 'adult_count', and 'kid_count'.\n"
                "- TRAVELER IDENTIFICATION: Identify the number of adults and children from the chat. If not mentioned, default to 1 adult and 0 kids.\n"
                "- 'assistant_message': A brief, friendly conversational response. Use PLAIN TEXT ONLY. Strictly NO markdown (#, ###, **, etc.).\n"
                "- 'itinerary': List of 5-7 objects. Each MUST have: 'id', 'time_range', 'description', and 'local_price' (The raw numeric value found in search results, e.g., 500 for 500 INR).\n"
                "- DENSITY: Prioritize a packed schedule. Even if walking takes 200 minutes, assume the user will take a car/taxi to fit in 5-7 stops.\n"
                "- TRAVEL TIMES: Do NOT calculate or include any travel times (car, foot, transit) in your JSON. These are handled automatically by the system.\n"
                "- DESCRIPTION RULE: The 'description' MUST be exactly 3 sentences. Do NOT mention the name of the place or any budget/price information in the description.\n"
                "- STRICTLY PROHIBITED: 'Optional' activities, alternatives, or 'if time permits' suggestions. Provide exactly one definitive path.\n"
                ),
        }
    
        context_msg = {
            "role": "user",
            "content": (
                f"Context:\n- Budget: {budget_val:.2f} {currency}\n- Search center (ll): {ll}\n- Search radius: {radius} m\n- Traveler Profile: {persona}\n\n"
                "Plan a day trip for today based on my preferences in this chat."
            ),
        }
    
        convo = [system_msg] + messages + [context_msg]

        # --- Phase 1: Discovery ---
        resp = client.chat.completions.create(model=st.session_state.model, messages=convo, tools=tools, tool_choice="auto")
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        conversion_rate, local_currency_code = db_future.result()

        if not tool_calls:
            return (msg.content or ""), found_places, [], conversion_rate, local_currency_code

        convo.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in tool_calls]})

        def execute_tool(tc):
            fn, args = tc.function.name, json.loads(tc.function.arguments or "{}")
            if fn == "google_search_places":
                out = google_search_places(f"{args.get('query')} in {city}", args.get("ll", ll), int(args.get("radius", radius)), 5)
                return tc.id, out, (out.get("results", []) if not out.get("error") else [])
            return tc.id, {"error": True}, []

        for tc_id, out, new_places in executor.map(execute_tool, tool_calls):
            if new_places: found_places.extend(new_places)
            convo.append({"role": "tool", "tool_call_id": tc_id, "content": json.dumps(out)})

        # --- Phase 2: Enrichment ---
        enriched_data = []
        if found_places:
            price_futures = {executor.submit(serper_search_prices, f"entrance fee {p['name']} {p['address']}"): p for p in found_places}
            for future in concurrent.futures.as_completed(price_futures):
                p, res = price_futures[future], future.result()
                enriched_data.append({"place": p['name'], "price_info": res.get("organic", [])[:3]})
            
            convo.append({"role": "system", "content": f"CRITICAL PRICE DATA: {json.dumps(enriched_data)}\nDETEERMINISTIC CONVERSION: Rate 1 EUR = {conversion_rate} {local_currency_code}. Divide local price by {conversion_rate}."})

        # --- Phase 3: Synthesis ---
        time.sleep(1.5)
        final_resp = client.chat.completions.create(model=st.session_state.model, messages=convo, response_format={"type": "json_object"})
        return final_resp.choices[0].message.content or "", found_places, enriched_data, conversion_rate, local_currency_code


# ---------- Streamlit UI ----------
def create_styled_popup(place, index):
    """Create beautiful HTML popup with CSS styling"""
    
    # Create scrolling image gallery
    images_html = ""
    if place.get('photo_urls'):
        imgs = "".join([f'<img src="{url}" style="width:100%; height:140px; object-fit:cover; border-radius:4px; flex-shrink:0; scroll-snap-align: start;">' for url in place['photo_urls']])
        images_html = f"""
        <div style="display: flex; gap: 8px; overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 8px; margin-bottom: 8px; scrollbar-width: thin;">
            {imgs}
        </div>
        """

    desc_html = f'<p style="margin: 8px 0; color: #666; font-size: 12px; font-style: italic;">{place["description"]}</p>' if place.get('description') else ''

    popup_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; width: 280px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 12px; 
                    border-radius: 8px 8px 0 0; 
                    margin: -10px -10px 10px -10px;">
            <h3 style="color: white; margin: 0; font-size: 16px; font-weight: 600;">
                {index}. {place['name']}
            </h3>
        </div>
        
        <div style="padding: 0 5px;">
            {images_html}
            {desc_html}
            <p style="margin: 8px 0; color: #444; font-size: 13px;">
                <i class="fa fa-map-marker" style="color: #667eea; margin-right: 6px;"></i>
                {place.get('address', 'Address not available')}
            </p>
            
            {f'''<p style="margin: 8px 0; font-size: 13px;">
                <i class="fa fa-phone" style="color: #667eea; margin-right: 6px;"></i>
                <a href="tel:{place['tel']}" style="color: #667eea; text-decoration: none;">
                    {place['tel']}
                </a>
            </p>''' if place.get('tel') else ''}
            
            {f'''<p style="margin: 8px 0; font-size: 13px;">
                <i class="fa fa-globe" style="color: #667eea; margin-right: 6px;"></i>
                <a href="{place['website']}" target="_blank" 
                   style="color: #667eea; text-decoration: none;">
                    Visit Website
                </a>
            </p>''' if place.get('website') else ''}
        </div>
    </div>
    """
    return popup_html


def create_beautiful_map(map_info, radius, center_ll):
    """Create an enhanced, beautiful map with professional styling"""
    
    # Use Google Maps style tiles
    m = folium.Map(
        location=center_ll,
        zoom_start=14,
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
    )
    
    # Add alternative tile layers
    folium.TileLayer(
        tiles='CartoDB Positron',
        name='Light Mode',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='CartoDB Dark_Matter',
        name='Dark Mode',
        control=True
    ).add_to(m)
    
    bounds = []
    route_points = []
    
    # Add numbered markers for each place
    for idx, p in enumerate(map_info["places"], 1):
        lat, lon = p.get("latitude"), p.get("longitude")
        if lat and lon:
            route_points.append([lat, lon])
            
            popup_html = create_styled_popup(p, idx)
            
            icon = BeautifyIcon(
                prefix='fa',
                icon_shape='marker',
                icon='',
                background_color='red',
                border_color='red',
                text_color='white',
                inner_icon_style='font-size:16px;padding-top:6px;'
            )
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=folium.Tooltip(
                    f"<div style='font-family: sans-serif; font-weight: 600; font-size: 12px; color: #333; background-color: white; border: 2px solid #667eea; border-radius: 4px; padding: 2px 6px; box-shadow: 2px 2px 6px rgba(0,0,0,0.1); white-space: nowrap; max-width: 150px; overflow: hidden; text-overflow: ellipsis;'>{idx}. {p['name']}</div>",
                    permanent=True,
                    direction="right",
                    offset=(0, -20),
                    sticky=False,
                    interactive=True,
                    className="fixed-label"
                ),
                icon=icon
            ).add_to(m)
            
            bounds.append([lat, lon])
    
    # Fit map bounds
    if len(bounds) > 1:
        m.fit_bounds(bounds, padding=(50, 50))
    
    # Draw the walking route - THIS IS THE KEY SECTION
    if len(route_points) > 1:
        # Optimization is handled in the main loop before calling this, 
        # but we call it here for the polyline rendering
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        route_res = get_route_google(route_points, api_key, optimize=False)
        path_latlon = route_res["polyline"]
        
        if not path_latlon:
            path_latlon = get_route_osrm(route_points)
        
        # Draw the route
        if path_latlon and len(path_latlon) > 0:
            # Main route line (blue)
            folium.PolyLine(
                path_latlon,
                color='#4A90E2',
                weight=5,
                opacity=0.8,
                tooltip="Walking Route",
                smooth_factor=1
            ).add_to(m)
            
            # Shadow effect (darker blue behind)
            folium.PolyLine(
                path_latlon,
                color='#2E5C8A',
                weight=7,
                opacity=0.3,
                smooth_factor=1
            ).add_to(m)
        else:
            # Fallback: draw straight lines if no route available
            folium.PolyLine(
                route_points,
                color='#95A5A6',
                weight=3,
                dash_array='8, 4',
                opacity=0.7,
                tooltip="Direct path (route unavailable)"
            ).add_to(m)
    
    # Add controls
    folium.LayerControl(position='topright').add_to(m)
    Fullscreen(position='topleft').add_to(m)
    m.add_child(MeasureControl(primary_length_unit='meters', secondary_length_unit='miles'))
    # Inject CSS directly into the map to hide the speech bubble
    map_css = """
    <style>
    .leaflet-tooltip {
        background: none !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        pointer-events: auto !important;
        transition: none !important;
        animation: none !important;
        margin: 0 !important;
    }
    .leaflet-tooltip-pane {
        transition: none !important;
    }
    .leaflet-tooltip-top:before, .leaflet-tooltip-bottom:before,
    .leaflet-tooltip-left:before, .leaflet-tooltip-right:before {
        display: none !important;
    }
    </style>
    <script>
    setTimeout(function() {
        var maps = document.querySelectorAll('.leaflet-container');
        maps.forEach(function(map_el) {
            var map = map_el._leaflet_map;
            map.eachLayer(function(layer) {
                if (layer instanceof L.Marker && layer.getTooltip()) {
                    var tt = layer.getTooltip();
                    if (tt._container) {
                        tt._container.style.cursor = 'pointer';
                        tt._container.onclick = function() { layer.openPopup(); };
                    }
                }
            });
        });
    }, 500);
    </script>
    """
    m.get_root().header.add_child(folium.Element(map_css))

    return m

def generate_itinerary_pdf(messages, city, country):
    """Extracts the last itinerary and generates a PDF"""
    try:
        from weasyprint import HTML
    except ImportError:
        print("DEBUG: WeasyPrint (GTK Runtime) not found. PDF generation skipped.")
        return None
    except OSError:
        print("DEBUG: GTK DLLs not found in Path. Please install GTK Runtime.")
        return None

    itinerary_text = next((m["content"] for m in reversed(messages) if m["role"] == "assistant" and "###" in m["content"]), None)
    if not itinerary_text:
        return None

    # Convert Markdown-style text to basic HTML for WeasyPrint
    html_body = itinerary_text.replace("### ", "<h2>").replace("###", "<h2>")
    html_body = html_body.replace("**", "<b>").replace("\n", "<br>")

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ 
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji';
                line-height: 1.6; color: #333; padding: 40px; 
            }}
            h1 {{ color: #1a237e; text-align: center; border-bottom: 2px solid #1a237e; padding-bottom: 10px; }}
            h2 {{ color: #283593; margin-top: 20px; font-size: 18px; border-bottom: 1px solid #eee; }}
            b {{ color: #000; }}
        </style>
    </head>
    <body>
        <h1>Day Trip Itinerary: {city}, {country}</h1>
        <div>{html_body}</div>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()


def show_trip_planner():
    load_dotenv()
    try:
        st.set_page_config(
            page_title="🗺️Trip Planner",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except:
        pass

    # CSS to perfectly align the columns and remove default margins
    st.markdown("""
        <style>
            .stMarkdown h3 {
                margin-top: 0rem !important;
                padding-top: 0rem !important;
                margin-bottom: 0.5rem !important;
            }
            [data-testid="stVerticalBlock"] > div:has(div[data-testid="stVerticalBlock"]) {
                padding-top: 0rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🗺️Trip Planner")
    
    # API key checks
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Missing OPENAI_API_KEY in environment/.env")
        st.stop()
    
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        st.error("Missing GOOGLE_MAPS_API_KEY in environment/.env")
        st.stop()
    
    # Settings moved from sidebar to main area so they only appear within this tab
    with st.expander("Trip Settings", expanded=True):
        # Strip names after commas normally, but for Congo only remove the comma to keep both republics distinct
        name_to_code = {
            (c.name.replace(',', '') if "Congo" in c.name else c.name.split(',')[0]): c.alpha_2 
            for c in pycountry.countries
        }
        country_list = sorted(list(name_to_code.keys()))
        # Set the default country to the one selected in the main travel planner
        current_sel = st.session_state.get('selected_country', {}).get('country_name', 'Germany')
        default_country_name = current_sel.replace(',', '') if "Congo" in current_sel else current_sel.split(',')[0]
        if default_country_name not in country_list:
            st.error(f"Unfortunately, {current_sel} is not available for the trip planner yet.")
            st.stop()

        default_country_idx = country_list.index(default_country_name)
        selected_country = st.selectbox("Select Country", options=country_list, index=default_country_idx)
            
        gc = geonamescache.GeonamesCache()
        country_code = name_to_code.get(selected_country, "DE")
        country_obj = pycountry.countries.get(alpha_2=country_code)
        iso3 = country_obj.alpha_3 if country_obj else "DEU"

        country_info = gc.get_countries().get(country_code)
        capital_city = country_info.get('capital') if country_info else ""
        
        city_data = [c['name'] for c in gc.get_cities().values() if c['countrycode'] == country_code]
        city_list = sorted(list(set(city_data)))
        
        if city_list:
            # Normalize function to strip accents (e.g., Brasília -> brasilia)
            norm = lambda s: ''.join(c for c in unicodedata.normalize('NFD', s or "") if unicodedata.category(c) != 'Mn').lower()
            objs = [c for c in gc.get_cities().values() if c['countrycode'] == country_code]
            # 1. Try exact name match, 2. Try normalized match, 3. Fallback to largest city
            best = next((c['name'] for c in objs if c['name'] == capital_city), None)
            if not best:
                best = next((c['name'] for c in objs if norm(c['name']) == norm(capital_city)), None)
            if not best and objs:
                best = max(objs, key=lambda x: x['population'])['name']
            default_idx = city_list.index(best) if best in city_list else 0
            selected_city = st.selectbox("Select City", options=city_list, index=default_idx)
        else:
            selected_city = st.text_input("Type City Name", value="Berlin")
        
        geolocator = Nominatim(user_agent="day_trip_planner")
        try:
            search_country = selected_country.split(',')[0]
            location = geolocator.geocode(f"{selected_city}, {search_country}", timeout=10)
        except Exception as e:
            st.warning(f"Geocoding service unavailable: {e}")
            location = None
        
        if location:
            ll = f"{location.latitude},{location.longitude}"
        else:
            st.error("Location not found. Using fallback.")
            ll = "49.7500,8.6500"
        
        radius = st.slider("Search radius (m)", 500, 20000, 5000, step=500)
        currency_symbol = st.session_state.get('currency_symbol', '€')
        budget = st.number_input(f"Budget ({currency_symbol})", min_value=0.0, value=40.0, step=5.0)

    # --- Fix: Reset chat if location changes to prevent Mannheim/Weinheim contamination ---
    current_location_key = f"{selected_country}-{selected_city}"
    if st.session_state.get("last_location_key") != current_location_key:
        st.session_state.messages = [
            {"role": "assistant", "content": f"I'm ready to plan your trip in {selected_city}, {selected_country}! Would you like to enjoy sightseeing, shopping, great restaurants or something else?"}
        ]
        st.session_state.map_data = {"places": [], "center": None}
        st.session_state.last_location_key = current_location_key
        st.rerun()
    
    if "model" not in st.session_state:
        st.session_state.model = "gpt-5-nano-2025-08-07"
    
    # Chat state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Tell me your interests (e.g., nature, cafés, museums) and any constraints (time window, kids, mobility).",
            }
        ]
    
    if "map_data" not in st.session_state:
        st.session_state.map_data = {"places": [], "center": None}
    
    # Layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Scrollable container for chat history
        with st.container(height=650):
            for i, m in enumerate(st.session_state.messages):
                is_last = (i == len(st.session_state.messages) - 1)
                with st.chat_message(m["role"]):
                    if is_last:
                        # Invisible anchor for the scrolling script
                        st.markdown('<div id="latest-message"></div>', unsafe_allow_html=True)
                    st.markdown(m["content"])

            prompt = st.chat_input("What kind of day trip do you want?")

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Planning your trip..."):
                        planner_messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                            if m["role"] in ("user", "assistant")
                        ]
                        
                        persona = st.session_state.get('selected_persona', 'General Traveler')
                        raw_json, places, prices_list, rate, local_curr = run_planner(
                             planner_messages, ll=ll, radius=radius, budget_val=budget, 
                             persona=persona, currency=currency_symbol, city=selected_city, 
                             iso3=iso3
                        )
                        try:
                            data = json.loads(raw_json)
                        except:
                            data = {}                                   

                        st.session_state.map_data = {"places": [], "center": ll}
                        
                        # 1. Show Assistant Message
                        # Aggressively strip markdown characters to ensure plain text rendering
                        assistant_text = data.get("assistant_message", "").replace("#", "").replace("*", "").replace("_", "").strip()
                        if assistant_text:
                            st.write(assistant_text)
                        
                        itinerary_md = ["---"]
                        total_day_cost = 0

                        # --- NEW: ROUTE OPTIMIZATION LOGIC ---
                        if isinstance(data, dict) and "itinerary" in data and len(data["itinerary"]) > 2:
                            # 1. Resolve all places first to get coordinates
                            temp_itinerary = []
                            coords = []
                            
                            def find_match_pre(eid, edesc):
                                for p in places:
                                    if p["place_id"] == eid or eid in p["place_id"]: return p
                                    if p["name"].lower() == eid.lower(): return p
                                    if p["name"].lower() in edesc.lower(): return p
                                return None

                            for entry in data["itinerary"]:
                                m = find_match_pre(entry.get("id", ""), entry.get("description", ""))
                                if m:
                                    temp_itinerary.append({"entry": entry, "match": m})
                                    coords.append([m["latitude"], m["longitude"]])
                            
                            if len(coords) > 2:
                                api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
                                opt_res = get_route_google(coords, api_key, optimize=True)
                                opt_idx = opt_res["optimized_indices"] # e.g. [1, 0] for intermediates
                                
                                if opt_idx:
                                    # Reconstruct: Origin (0) + Optimized Intermediates + Destination (last)
                                    new_order = [0] + [i + 1 for i in opt_idx] + [len(coords) - 1]                                    
                                    # Preserve original time slots in order
                                    time_slots = [e["entry"]["time_range"] for e in temp_itinerary]
                                    
                                    optimized_itinerary = []
                                    for i, original_pos in enumerate(new_order):
                                        item = temp_itinerary[original_pos]
                                        item["entry"]["time_range"] = time_slots[i] # Re-assign time slot
                                        optimized_itinerary.append(item["entry"])
                                    
                                    data["itinerary"] = optimized_itinerary
                                    print(f"DEBUG: Route optimized. New sequence: {new_order}")                        

                        # Get traveler counts from AI response
                        adults = data.get("adult_count", 1)
                        kids = data.get("kid_count", 0)
                        multiplier = adults + (kids * 0.5)         
                        print(f"DEBUG TRAVELERS: Adults={adults}, Kids={kids}, Multiplier={multiplier}")               
                        
                        if isinstance(data, dict) and "itinerary" in data:
                            for entry in data["itinerary"]:
                                pid = entry.get("id")
                                # Robust matching helper: checks ID, partial ID, and Name-as-ID
                                def find_match(e):
                                    eid = e.get("id", "")
                                    edesc = e.get("description", "").lower()
                                    if not eid: return None
                                    for p in places:
                                        p_id = p["place_id"]
                                        p_name = p["name"].lower()
                                        
                                        # 1. Match against Google Place ID
                                        if p_id == eid or eid in p_id: return p
                                        # 2. Match against Name (if AI used name as ID)
                                        if p_name == eid.lower() or eid.lower() in p_name: return p
                                        # 3. Fallback: Name is in the description
                                        if p_name in edesc: return p
                                    return None

                                match = find_match(entry)
                                if match:
                                    # Add to Map
                                    st.session_state.map_data["places"].append(match)
                                    
                                    # Build Markdown using official name
                                    name = match.get("name", "Unknown Place")
                                    time = entry.get("time_range", "TBD")
                                    desc = entry.get("description", "")

                                    # --- Deterministic Travel Logic (Google Only) ---
                                    current_idx = data["itinerary"].index(entry)
                                    t_car, t_bus, t_walk = None, None, None
                                    
                                    # If there is a next stop, calculate travel TO it
                                    if current_idx < len(data["itinerary"]) - 1:
                                        next_entry = data["itinerary"][current_idx + 1]
                                        next_match = find_match(next_entry)
                                        
                                        if next_match:
                                            origin = [match["latitude"], match["longitude"]]
                                            destination = [next_match["latitude"], next_match["longitude"]]
                                            real_times = get_deterministic_durations(origin, destination)
                                            t_car = real_times["travel_car"]
                                            t_bus = real_times["travel_transit"]
                                            t_walk = real_times["travel_foot"]
                                            print(f"DEBUG TRAVEL TIMES: Stop='{name}' -> Next Stop | Foot: {t_walk}, Public: {t_bus}, Car: {t_car}")

                                    # Post-AI Assembly: Pull price from Serper data, not AI imagination
                                    # Deterministic Price Calculation in Python
                                    local_val = entry.get("local_price", 0)
                                    # Calculate per-person price then multiply by deterministic traveler count
                                    base_price_eur = (local_val / rate) if rate > 0 else local_val
                                    price_eur = int(math.ceil(base_price_eur * multiplier))
                                    print(f"DEBUG PRICE CALC: Place='{name}' | Local={local_val} {local_curr} | Rate={rate} | Base EUR={base_price_eur:.2f} | Mult={multiplier} | Final EUR={price_eur}")

                                    total_day_cost += price_eur    

                                    print(f"DEBUG CURRENCY: Place='{name}' | Original: {local_val} {local_curr} | Converted: {price_eur} EUR (Rate: {rate})")
                                    
                                    # Start building the stop markdown
                                    stop_md = f"### {time} - {name}\n"
                                    stop_md += f"- 📝 **Description**: {desc}\n"
                                    stop_md += f"- 💰 **Estimated Cost**: {currency_symbol}{price_eur}.00\n"
                                    
                                    # Only append travel info if there is a next stop
                                    if t_walk:
                                        stop_md += "- 🚶 **Travel to next stop**:\n"
                                        stop_md += f"  - 🏃 Foot: {t_walk}\n"
                                        stop_md += f"  - 🚌 Public Transport: {t_bus}\n"
                                        stop_md += f"  - 🚗 Car: {t_car}\n"
                                    st.markdown(stop_md)
                                    itinerary_md.append(stop_md)
                                else:
                                    # Fallback if AI hallucinates an ID from a previous city
                                    print(f"DEBUG: AI suggested ID {pid} which was not found in current results.")            

                        # Append Total Cost
                        total_md = f"### 💰 Total Estimated Day Cost: {currency_symbol}{total_day_cost}.00"
                        st.markdown(total_md)
                        itinerary_md.append(total_md)                                                            

                        answer = "\n".join(itinerary_md)
                        if not itinerary_md: answer = raw_json

                        st.session_state.messages.append({"role": "assistant", "content": f"{assistant_text}\n\n{answer}"})
                        st.rerun()

        # Download PDF Button (Bottom of Column 1)
        if len(st.session_state.messages) > 1:
            pdf_data = generate_itinerary_pdf(st.session_state.messages, selected_city, selected_country)
            if pdf_data:
                st.markdown("""
                    <style>
                        .pdf-download-container {
                            margin-top: -30px !important;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                col_pdf, _ = st.columns([0.5, 0.5])
                with col_pdf:
                    st.download_button(
                        label="📄 Download Itinerary (PDF)",
                        data=bytes(pdf_data),
                        file_name=f"itinerary_{selected_city}.pdf",
                        mime="application/pdf",
                        key="pdf_download"
                    )                        

        # JavaScript to snap the latest message to the top of the container
        components.html(
            """
            <script>
                var element = window.parent.document.getElementById('latest-message');
                if (element) {
                    element.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            </script>
            """,
            height=0
        )
            
    with col2:
        map_info = st.session_state.map_data
        
        if map_info["center"]:
            center_ll = [float(x) for x in map_info["center"].split(",")]
            print(f"DEBUG: Number of places: {len(map_info['places'])}")
            for i, p in enumerate(map_info["places"]):
                print(f"  Place {i+1}: {p['name']} at {p.get('latitude')}, {p.get('longitude')}")
            m = create_beautiful_map(map_info, radius, center_ll)
            
            st_folium(
                m, 
                width=None, 
                use_container_width=True, 
                height=650, 
                key="persistent_map",
                returned_objects=[]  # This prevents the rerun on click
            )

            # Construct Google Maps Directions URL at the bottom of the map column
            if len(st.session_state.map_data["places"]) >= 2:
                p_list = st.session_state.map_data["places"]
                origin = f"{p_list[0]['latitude']},{p_list[0]['longitude']}"
                destination = f"{p_list[-1]['latitude']},{p_list[-1]['longitude']}"
                waypoints = "|".join([f"{p['latitude']},{p['longitude']}" for p in p_list[1:-1]])
                gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode=walking"
                
                # Inject CSS to make the button more compact and match Pathfind colors
                st.markdown("""
                    <style>
                        .stLinkButton {
                            margin-top: -30px !important;
                        }
                        .stLinkButton > a {
                            height: 32px !important;
                            font-size: 13px !important;
                            background: linear-gradient(135deg, #f5f7fa 0%, #f0f3f8 100%) !important;
                            color: #333 !important;
                            border: 2px solid #e0e5ed !important;
                            border-radius: 10px !important;
                            text-decoration: none !important;
                            font-weight: 600 !important;
                            display: inline-flex !important;
                            align-items: center !important;
                            transition: all 0.3s ease !important;
                        }
                        .stLinkButton > a:hover {
                            background: linear-gradient(135deg, #1a237e 0%, #283593 100%) !important;
                            color: white !important;
                            border-color: #1a237e !important;
                            box-shadow: 0 4px 12px rgba(26, 35, 126, 0.2) !important;
                        }
                    </style>
                """, unsafe_allow_html=True)

                # Align button to the left
                col_btn, _ = st.columns([0.5, 0.5])
                with col_btn:
                    st.link_button("🌍 Open in Google Maps", gmaps_url)
        else:
            st.info("🎯 The map will appear here once a trip is planned.")
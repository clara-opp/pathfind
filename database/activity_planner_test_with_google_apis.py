import os
import re
import json
import requests
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
        
        return {"error": False, "results": results}
    
    except Exception as e:
        return {"error": True, "message": str(e)}


# ---------- Helper: Google Routes API ----------
def get_route_google(coordinates, api_key):
    """
    Get walking route using Google Routes API.
    coordinates: List of [lat, lon] pairs.
    Returns: List of [lat, lon] points representing the walking path.
    """
    if len(coordinates) < 2:
        return []
    
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline"
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
        "travelMode": "WALK",
        "polylineQuality": "HIGH_QUALITY"
    }
    
    if waypoints:
        data["intermediates"] = waypoints
    
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            response_data = r.json()
            routes = response_data.get("routes", [])
            if routes:
                encoded = routes[0].get("polyline", {}).get("encodedPolyline", "")
                if encoded:
                    return polyline.decode(encoded)
    except Exception:
        pass
    
    return []


# ---------- Fallback: OSRM Routing ----------
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


def serper_search_prices(query: str):
    """Search the web for current prices, entrance fees, or menu costs."""
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        return {"error": "Missing SERPER_API_KEY"}
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json={"q": query}, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ---------- OpenAI tool-calling loop ----------
def run_planner(messages, ll: str, radius: int, budget_eur: float):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
    found_places = []
    
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
        {
            "type": "function",
            "function": {
                "name": "serper_search_prices",
                "description": "Search the web for real-world prices, entrance fees, or menu costs for a specific venue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Price-related query, e.g., 'Louvre museum entrance fee 2024'."},
                    },
                    "required": ["query"],
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
            "- Use google_search_places to fetch real nearby places. You MUST generate ALL search queries for the entire day (morning, afternoon, evening) if not specified otherwise by the user.\n"
            "- EVERY trip plan MUST include food recommendations for each day: 1 breakfast spot for the morning, 1 lunch option (restaurant or street food), and 1 dinner option (restaurant or street food).\n"
            "- Use serper_search_prices to find actual costs for activities, entrance fees, or meals. Run these in the same turn as the place searches.\n"
            "- Target spending: Aim for a total cost between 85% and 90% of the budget. Never exceed the budget.\n"
            "- You MUST use serper_search_prices for every paid activity. Do not include disclaimers like 'could not be retrieved'; if a tool fails, use your best estimate based on the search results without mentioning the failure.\n"
            "- Return a JSON object with two keys: 'locations' then 'itinerary'. The 'locations' key MUST come first.\n"
            "- The 'locations' array MUST contain an entry for EVERY numbered stop in your itinerary. Use the exact 'place_id' from the tools for the 'id' field.\n"
            "- The 'itinerary' MUST be a numbered list (1., 2., 3., etc.). Do not use bullet points for main stops.\n"
            "- Every trip MUST include logical stops for meals (restaurant) and refreshments (cafe).\n"
            "- The 'itinerary' MUST be a string formatted with Markdown: each stop starts with a '### Time Range - Place Name' headline, followed by bullet points for ' - Description: [One liner describing the place and activities]' and ' - Price: [Price for the location]'.\n"
            "- STRICTLY PROHIBITED: 'Optional' activities, alternatives, or 'if time permits' suggestions. Provide exactly one definitive path.\n"
            ),
    }
    
    context_msg = {
        "role": "user",
        "content": (
            f"Context:\n- Budget: {budget_eur:.2f} EUR\n- Search center (ll): {ll}\n- Search radius: {radius} m\n\n"
            "Plan a day trip for today based on my preferences in this chat."
        ),
    }
    
    convo = [system_msg] + messages + [context_msg]
    
    # --- Phase 1: Discovery (Get Search Queries) ---
    resp = client.chat.completions.create(
        model=st.session_state.model,
        messages=convo,
        tools=tools,
        tool_choice="auto",
    )
    
    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None)

    if tool_calls:
        convo.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in tool_calls],
            }
        )            
            
        def execute_tool(tc):
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                
                if fn == "google_search_places":
                    out = google_search_places(
                        query=args.get("query", ""),
                        ll=args.get("ll", ll),
                        radius=int(args.get("radius", radius)),
                        limit=int(args.get("limit", 8)),
                    )
                    # Return places separately to update main list safely
                    return tc.id, out, out.get("results", []) if not out.get("error") else []
                elif fn == "serper_search_prices":
                    out = serper_search_prices(query=args.get("query", ""))
                    return tc.id, out, []
                else:
                    return tc.id, {"error": True, "message": f"Unknown tool: {fn}"}, []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Execute in parallel, preserve order for conversation history
            results = executor.map(execute_tool, tool_calls)
            
            for tc_id, out, new_places in results:
                if new_places:
                    found_places.extend(new_places)
                convo.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps(out, ensure_ascii=False),
                })

        # --- Phase 2: Synthesis (Generate Itinerary) ---
        final_resp = client.chat.completions.create(
            model=st.session_state.model,
            messages=convo,
            tools=tools,
            tool_choice="none", # Force text generation, no more tools
            response_format={"type": "json_object"},
            stream=False,
        )
        return final_resp.choices[0].message.content or "", found_places

    # If no tools were called in Phase 1, return the initial text
    return (msg.content or "(No response text.)"), found_places


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
        # Try Google Routes API first
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        path_latlon = get_route_google(route_points, api_key)
        
        # Fallback to OSRM if Google fails
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


def main():
    load_dotenv()
    st.set_page_config(
        page_title="🗺️Trip Planner",
        layout="wide",
        initial_sidebar_state="expanded"
    )

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
    
    with st.sidebar:
        st.header("🌍Trip settings")
        
        with st.container(border=True):
            country_list = sorted([c.name for c in pycountry.countries])
            selected_country = st.selectbox("Select Country", options=country_list, index=country_list.index("Germany"))
            
            gc = geonamescache.GeonamesCache()
            country_obj = pycountry.countries.get(name=selected_country)
            country_code = country_obj.alpha_2 if country_obj else "DE"

            country_info = gc.get_countries().get(country_code)
            capital_city = country_info.get('capital') if country_info else ""
            
            city_data = [c['name'] for c in gc.get_cities().values() if c['countrycode'] == country_code]
            city_list = sorted(list(set(city_data)))
            
            if city_list:
                default_idx = city_list.index(capital_city) if capital_city in city_list else 0
                selected_city = st.selectbox("Select City", options=city_list, index=default_idx)
            else:
                selected_city = st.text_input("Type City Name", value="Berlin")
            
            geolocator = Nominatim(user_agent="day_trip_planner")
            try:
                location = geolocator.geocode(f"{selected_city}, {selected_country}", timeout=10)
            except Exception as e:
                st.warning(f"Geocoding service unavailable: {e}")
                location = None
            
            if location:
                ll = f"{location.latitude},{location.longitude}"
            else:
                st.error("Location not found. Using fallback.")
                ll = "49.7500,8.6500"
            
            radius = st.slider("Search radius (m)", 500, 20000, 5000, step=500)
            budget = st.number_input("Budget (EUR)", min_value=0.0, value=40.0, step=5.0)
        
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
                        
                        raw_json, places = run_planner(planner_messages, ll=ll, radius=radius, budget_eur=budget)
                        try:
                            data = json.loads(raw_json)
                        except:
                            data = {}                        
                        st.session_state.map_data = {"places": [], "center": ll}
                        for loc in (data.get("locations", []) if isinstance(data, dict) else []):
                            pid = loc.get("id")
                            match = next((p for p in places if p["place_id"] == pid), None)
                            if match:
                                st.session_state.map_data["places"].append(match)
                        answer = data.get("itinerary", raw_json) if isinstance(data, dict) else raw_json

                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.rerun()

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
            
            st_folium(m, width="100%", height=650, key="persistent_map")
        else:
            st.info("🎯 The map will appear here once a trip is planned.")


if __name__ == "__main__":
    main()
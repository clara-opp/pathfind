import os
import json
import requests
import streamlit as st
from geopy.geocoders import Nominatim
import pycountry
import geonamescache
import folium
from streamlit_folium import st_folium
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
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri,places.nationalPhoneNumber"
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
            return {"error": True, "status": r.status_code, "body": r.text}
        
        response_data = r.json()
        results = []
        
        for p in response_data.get("places", []):
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
        }
    ]
    
    system_msg = {
        "role": "system",
        "content": (
            "You are a day-trip planner.\n"
            "Goal: propose a realistic day-trip itinerary within the user's fixed budget.\n"
            "Rules:\n"
            "- Use google_search_places to fetch real nearby places before recommending venues.\n"
            "- Google Places results do not include exact prices; clearly mark any costs as estimates.\n"
            "- Provide a per-item cost estimate and a running total not exceeding the budget.\n"
            "- Return a compact itinerary with times, travel notes, and place addresses.\n"
            "- IMPORTANT: When recommending a place, use its exact name from the search results so it can be mapped.\n"
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
    
    for _ in range(6):
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
            
            for tc in tool_calls:
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                
                if fn == "google_search_places":
                    out = google_search_places(
                        query=args.get("query", ""),
                        ll=args.get("ll", ll),
                        radius=int(args.get("radius", radius)),
                        limit=int(args.get("limit", 8)),
                    )
                    if not out.get("error"):
                        found_places.extend(out.get("results", []))
                else:
                    out = {"error": True, "message": f"Unknown tool: {fn}"}
                
                convo.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(out, ensure_ascii=False),
                    }
                )
            continue
        
        return (msg.content or "(No response text.)"), found_places
    
    return "Planner stopped after too many tool calls.", []


# ---------- Streamlit UI ----------
def get_category_style(categories):
    cats_str = " ".join(categories).lower()
    if "park" in cats_str or "nature" in cats_str or "garden" in cats_str:
        return "tree", "green"
    elif "cafe" in cats_str or "coffee" in cats_str or "bakery" in cats_str:
        return "coffee", "beige"
    elif "museum" in cats_str or "gallery" in cats_str or "history" in cats_str:
        return "university", "purple"
    elif "restaurant" in cats_str or "food" in cats_str:
        return "cutlery", "red"
    elif "bar" in cats_str or "pub" in cats_str:
        return "glass", "darkblue"
    elif "shop" in cats_str or "store" in cats_str:
        return "shopping-bag", "orange"
    return "map-marker", "blue"


def main():
    load_dotenv()
    st.set_page_config(
        page_title="Day Trip Planner (OpenAI + Google Maps)",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("Day Trip Planner (Chat + Google Maps)")
    
    # API key checks
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Missing OPENAI_API_KEY in environment/.env")
        st.stop()
    
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        st.error("Missing GOOGLE_MAPS_API_KEY in environment/.env")
        st.stop()
    
    with st.sidebar:
        st.header("Trip settings")
        
        with st.expander("🌍 Location Selection", expanded=True):
            country_list = sorted([c.name for c in pycountry.countries])
            selected_country = st.selectbox("Select Country", options=country_list, index=country_list.index("Germany"))
            
            gc = geonamescache.GeonamesCache()
            country_obj = pycountry.countries.get(name=selected_country)
            country_code = country_obj.alpha_2 if country_obj else "DE"
            
            city_data = [c['name'] for c in gc.get_cities().values() if c['countrycode'] == country_code]
            city_list = sorted(list(set(city_data)))
            
            if city_list:
                default_idx = city_list.index("Berlin") if "Berlin" in city_list else 0
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
                st.success(f"Located: {location.latitude:.4f}, {location.longitude:.4f}")
            else:
                st.error("Location not found. Using fallback.")
                ll = "49.7500,8.6500"
            
            radius = st.slider("Search radius (m)", 500, 20000, 5000, step=500)
            budget = st.number_input("Budget (EUR)", min_value=0.0, value=40.0, step=5.0)
        
        st.header("Model")
        if "model" not in st.session_state:
            st.session_state.model = "gpt-4o-mini"
        st.session_state.model = st.text_input("OpenAI model", value=st.session_state.model)
        st.caption("Tip: Ask for a style (relaxed/packed), interests, and dietary needs.")
    
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
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
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
                    
                    answer, places = run_planner(planner_messages, ll=ll, radius=radius, budget_eur=budget)
                    
                    # Filter places mentioned in answer
                    unique_places = {p["place_id"]: p for p in places}.values()
                    final_places = [
                        p for p in unique_places
                        if p["name"].lower() in answer.lower()
                    ]
                    
                    st.session_state.map_data = {"places": final_places, "center": ll}
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.rerun()
    
    with col2:
        st.subheader("Trip Map")
        map_info = st.session_state.map_data
        
        if map_info["center"]:
            center_ll = [float(x) for x in map_info["center"].split(",")]
            m = folium.Map(location=center_ll, zoom_start=13, tiles="Cartodb Positron")
            
            folium.Circle(
                location=center_ll, radius=radius, color="#3388ff", weight=1,
                fill=True, fill_color="#3388ff", fill_opacity=0.1,
                tooltip=f"Search Radius: {radius}m"
            ).add_to(m)
            
            folium.Marker(
                center_ll, popup="Search Center", tooltip="Start Here",
                icon=folium.Icon(color="black", icon="home", prefix="fa")
            ).add_to(m)
            
            bounds = [center_ll]
            route_points = [center_ll]
            
            for p in map_info["places"]:
                lat, lon = p.get("latitude"), p.get("longitude")
                if lat and lon:
                    route_points.append([lat, lon])
                    icon_name, icon_color = get_category_style(p.get("categories", []))
                    
                    popup_html = f"<b>{p['name']}</b><br>{p.get('address', '')}"
                    folium.Marker(
                        [lat, lon],
                        popup=folium.Popup(popup_html, max_width=200),
                        tooltip=p["name"],
                        icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa")
                    ).add_to(m)
                    bounds.append([lat, lon])
            
            if len(bounds) > 1:
                m.fit_bounds(bounds, padding=(30, 30))
            
            # Draw route
            if len(route_points) > 1:
                # Try Google Routes API first
                api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
                path_latlon = get_route_google(route_points, api_key)
                
                # Fallback to OSRM if Google fails
                if not path_latlon:
                    path_latlon = get_route_osrm(route_points)
                
                if path_latlon:
                    folium.PolyLine(
                        path_latlon, color="blue", weight=4, opacity=0.7,
                        tooltip="Walking Path"
                    ).add_to(m)
                else:
                    folium.PolyLine(
                        route_points, color="gray", weight=2, dash_array="5, 5"
                    ).add_to(m)
            
            st_folium(m, width="100%", height=600, key="persistent_map")
        else:
            st.info("The map will appear here once a trip is planned.")


if __name__ == "__main__":
    main()

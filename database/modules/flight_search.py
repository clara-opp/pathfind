# modules/flight_search.py
"""
Flight Search / Booking / Confirmation module for the Global Travel Planner.

Goal:
- Keep the main app clean by moving ALL flight-related UI + logic here:
  1) Flight search UI + results + pricing confirmation
  2) Booking form + create order
  3) Confirmation screen + Google Calendar OAuth redirect + event creation
  4) OAuth callback handler (reads st.query_params, decodes state, creates calendar events)

Main app should only:
- import these functions
- pass dependencies (data_manager, amadeus module, calendar_client, credentials/keys, country, defaults)
- keep routing (step numbers) unchanged
"""

from __future__ import annotations

import streamlit as st
import datetime
import time
import random
import re
import json
import base64
from typing import Dict, Any, Optional, List, Union


# -----------------------------
# Small helpers
# -----------------------------
def format_duration(duration_str):
    if isinstance(duration_str, datetime.timedelta):
        total_seconds = int(duration_str.total_seconds())
        return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    match = re.match(r"PT(\d+H)?(\d+M)?", str(duration_str))
    h = match.group(1)[:-1] if match and match.group(1) else "0"
    m = match.group(2)[:-1] if match and match.group(2) else "0"
    return f"{h}h {m}m"


def parse_duration_to_td(duration_raw):
    match = re.match(r"PT(\d+H)?(\d+M)?", str(duration_raw))
    h, m = 0, 0
    if match:
        if match.group(1):
            h = int(match.group(1)[:-1])
        if match.group(2):
            m = int(match.group(2)[:-1])
    return datetime.timedelta(hours=h, minutes=m)


def _iata_from_display(display: str) -> str:
    """
    Your app uses format: "City (IATA)".
    In your existing code you did `orig_val[-4:-1]`.
    We'll do it safely with regex.
    """
    m = re.search(r"\(([A-Z0-9]{3})\)\s*$", str(display).strip())
    if m:
        return m.group(1)
    # fallback: keep your old behavior as last resort
    return str(display)[-4:-1]


def _date_value_from_manual_dates(dates_val, trip_type: str):
    """
    Manual date input can be single date or [start, end].
    Returns (departure_date, return_date_or_none)
    """
    if isinstance(dates_val, (list, tuple)):
        dep = dates_val[0]
        ret = dates_val[1] if (trip_type == "Round Trip" and len(dates_val) > 1) else None
    else:
        dep = dates_val
        ret = None
    return dep, ret


# -----------------------------
# Public API
# -----------------------------
def render_flight_search(
    *,
    country: Dict[str, Any],
    data_manager,
    amadeus,
    amadeus_api_key: str,
    amadeus_api_secret: str,
    currency_code: str,
    origin_iata_default: str,
    start_date_default: Optional[datetime.date],
    end_date_default: Optional[datetime.date],
    image_urls: Optional[List[str]] = None,
    key_prefix: str = "fs",
):
    """
    Renders the "Find Flights" tab UI and runs searches, shows filters/results,
    lets the user confirm pricing ("Book Flight") -> sets st.session_state.priced_offer and step=7.

    Keeps interface/behavior identical to what you had in main.
    """
    # -----------------------------
    # Session defaults (scoped)
    # -----------------------------
    # To avoid collisions, we store some internal keys with key_prefix
    expanded_key = f"{key_prefix}_search_expanded"
    label_key = f"{key_prefix}_expander_label"
    manual_trigger_key = f"{key_prefix}_manual_search_triggered"
    search_count_key = f"{key_prefix}_search_count"
    last_origin_key = f"{key_prefix}_last_search_origin"
    last_dest_key = f"{key_prefix}_last_search_dest"
    sort_by_key = f"{key_prefix}_sort_by"
    flight_results_key = f"{key_prefix}_flight_results"

    # traveler_counts are used later by booking step
    traveler_counts_key = f"{key_prefix}_traveler_counts"

    if expanded_key not in st.session_state:
        st.session_state[expanded_key] = True

    if label_key not in st.session_state:
        st.session_state[label_key] = "Flight Search Configuration"

    if manual_trigger_key not in st.session_state:
        st.session_state[manual_trigger_key] = False

    if search_count_key not in st.session_state:
        st.session_state[search_count_key] = 0

    # We keep your "unique_label" trick for expander rerenders
    unique_label = st.session_state[label_key] + ("\u200b" * int(st.session_state[search_count_key]))

    # -----------------------------
    # Config expander UI (same as before)
    # -----------------------------
    with st.expander(unique_label, expanded=st.session_state[expanded_key]):

        trip_type = st.selectbox(
            "Trip Type",
            ["Round Trip", "One Way"],
            key=f"{key_prefix}_search_trip_type",
        )

        all_airports = data_manager.get_airports()
        dest_airports = data_manager.get_airports(country["iso2"])

        c1, c2, c3 = st.columns(3)
        default_origin = origin_iata_default or "FRA"
        origin_index = (
            all_airports[all_airports["iata_code"] == default_origin].index[0]
            if not all_airports[all_airports["iata_code"] == default_origin].empty
            else 0
        )

        orig = c1.selectbox(
            "Flying from:",
            all_airports["display"],
            index=int(origin_index),
            key=f"{key_prefix}_manual_orig",
        )
        dest = c2.selectbox(
            "Flying to:",
            dest_airports["display"],
            key=f"{key_prefix}_manual_dest",
        )

        s_date = start_date_default or (datetime.date.today() + datetime.timedelta(days=14))
        e_date = end_date_default or (s_date + datetime.timedelta(days=3))

        if trip_type == "Round Trip":
            dates = c3.date_input(
                "Vacation Dates:",
                [s_date, e_date],
                key=f"{key_prefix}_manual_dates",
            )
        else:
            dates = c3.date_input(
                "Departure Date:",
                s_date,
                key=f"{key_prefix}_manual_dates",
            )

        c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1])
        t_class = c4.selectbox(
            "Class",
            ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
            key=f"{key_prefix}_manual_class",
        )
        ad = c5.number_input(
            "Adults (12y+)",
            1, 9, 1,
            key=f"{key_prefix}_manual_adults",
        )
        ch = c6.number_input(
            "Children (2-11y)",
            0, 9, 0,
            key=f"{key_prefix}_manual_children",
        )
        inf = c7.number_input(
            "Infants (<2y)",
            0, 9, 0,
            key=f"{key_prefix}_manual_infants",
        )
        non_stop = c8.checkbox(
            "Non-stop",
            key=f"{key_prefix}_manual_non_stop",
        )

        if st.button("Search Flights 🚀", use_container_width=True, key=f"{key_prefix}_manual_search_btn"):
            # Build a readable expander label (same behavior)
            l_orig = st.session_state[f"{key_prefix}_manual_orig"]
            l_dest = st.session_state[f"{key_prefix}_manual_dest"]

            t_str = f"{st.session_state[f'{key_prefix}_manual_adults']} Adult(s)"
            if st.session_state[f"{key_prefix}_manual_children"] > 0:
                t_str += f", {st.session_state[f'{key_prefix}_manual_children']} Child(ren)"
            if st.session_state[f"{key_prefix}_manual_infants"] > 0:
                t_str += f", {st.session_state[f'{key_prefix}_manual_infants']} Infant(s)"

            st.session_state[label_key] = f"{l_orig} - {l_dest}  \u2003·\u2003  {t_str}  \u2003·\u2003  {st.session_state[f'{key_prefix}_manual_class']}"
            st.session_state[sort_by_key] = "Price"
            st.session_state[search_count_key] += 1
            st.session_state[expanded_key] = False
            st.session_state[manual_trigger_key] = True
            st.session_state[last_origin_key] = l_orig
            st.session_state[last_dest_key] = l_dest
            st.rerun()

    # -----------------------------
    # Run search async-ish with image placeholder (same behavior)
    # -----------------------------
    if st.session_state[manual_trigger_key]:
        st.session_state[manual_trigger_key] = False

        img_placeholder = st.empty()

        orig_val = st.session_state[f"{key_prefix}_manual_orig"]
        dest_val = st.session_state[f"{key_prefix}_manual_dest"]
        dates_val = st.session_state[f"{key_prefix}_manual_dates"]

        st.session_state[traveler_counts_key] = {
            "ADULT": int(st.session_state[f"{key_prefix}_manual_adults"]),
            "CHILD": int(st.session_state[f"{key_prefix}_manual_children"]),
            "INFANT": int(st.session_state[f"{key_prefix}_manual_infants"]),
        }

        imgs = list(image_urls or [])
        imgs = [img for img in imgs if img]
        random.shuffle(imgs)

        dep_date, ret_date = _date_value_from_manual_dates(
            dates_val,
            trip_type=st.session_state.get(f"{key_prefix}_search_trip_type", "Round Trip"),
        )

        token = amadeus.get_amadeus_access_token(amadeus_api_key, amadeus_api_secret)

        params = {
            "originLocationCode": _iata_from_display(orig_val),
            "destinationLocationCode": _iata_from_display(dest_val),
            "departureDate": dep_date.strftime("%Y-%m-%d"),
            "returnDate": ret_date.strftime("%Y-%m-%d") if ret_date else None,
            # Passengers
            "adults": int(st.session_state[f"{key_prefix}_manual_adults"]),
            "children": int(st.session_state[f"{key_prefix}_manual_children"]),
            "infants": int(st.session_state[f"{key_prefix}_manual_infants"]),
            # Misc
            "travelClass": st.session_state[f"{key_prefix}_manual_class"],
            "nonStop": bool(st.session_state[f"{key_prefix}_manual_non_stop"]),
            "currencyCode": currency_code,
        }

        # we do the "threaded + rotating images" behavior exactly like you had:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(amadeus.search_flight_offers, token, params)

            img_idx = 0
            while not future.done():
                if imgs:
                    img_url = imgs[img_idx % len(imgs)]
                    img_placeholder.markdown(
                        f"""
                        <div style="text-align: center; animation: fadeIn 0.5s;">
                            <img src="{img_url}" style="width:100%; max-height:700px; object-fit:cover; border-radius:12px; margin-bottom:10px;">
                            <p style="color:gray; font-style:italic;">Searching for the best flights...</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    img_idx += 1

                for _ in range(50):
                    if future.done():
                        break
                    time.sleep(0.1)
                img_placeholder.empty()

        try:
            st.session_state[flight_results_key] = future.result()
        except Exception as e:
            st.error(f"Flight search failed: {e}")
            st.session_state[flight_results_key] = {"data": []}

    # -----------------------------
    # Render results (same behavior)
    # -----------------------------
    flight_results = st.session_state.get(flight_results_key)

    if not flight_results:
        return

    if not flight_results.get("data"):
        orig_label = st.session_state.get(last_origin_key, "Origin")
        dest_label = st.session_state.get(last_dest_key, "Destination")
        st.warning(
            f"No flights found for **{orig_label}** ✈️ **{dest_label}** for your selected vacation time. "
            "Please select a different airport or a different vacation time."
        )
        return

    maps = data_manager.get_iata_mappings()
    carriers = flight_results.get("dictionaries", {}).get("carriers", {})

    # Process summary dataframe (same as your logic)
    processed_data = []
    for idx, offer in enumerate(flight_results["data"]):
        outbound = offer["itineraries"][0]
        processed_data.append({
            "idx": idx,
            "Price": float(offer["price"]["total"]),
            "Currency": offer["price"]["currency"],
            "Duration": parse_duration_to_td(outbound["duration"]),
            "Carrier": carriers.get(outbound["segments"][0]["carrierCode"], "N/A"),
            "Layovers": len(outbound["segments"]) - 1,
            "Departure": datetime.datetime.fromisoformat(outbound["segments"][0]["departure"]["at"].replace("Z", "")),
        })

    # Lazy import pandas (main uses dynamic load; here we just import when needed)
    import pandas as pd

    df = pd.DataFrame(processed_data)

    if sort_by_key not in st.session_state:
        st.session_state[sort_by_key] = "Price"

    c_filters, c_results = st.columns([1, 3])

    with c_filters:
        st.markdown("##### Filters")

        # Use same symbols mapping
        symbol_map = {"EUR": "€", "USD": "$"}
        symbol = symbol_map.get(currency_code, currency_code)

        min_val = (int(df["Price"].min()) // 50) * 50
        max_val = ((int(df["Price"].max()) + 49) // 50) * 50
        if min_val == max_val:
            max_val += 50

        max_p = st.slider(
            "Price",
            min_val, max_val, max_val,
            step=50,
            format=f"%d {symbol}",
            key=f"{key_prefix}_filter_max_price",
        )

        max_dur_limit = int(df["Duration"].dt.total_seconds().max() / 3600) + 1
        max_dur = st.slider(
            "Duration (Hours)",
            1, max(max_dur_limit, 2), max_dur_limit,
            key=f"{key_prefix}_filter_max_dur",
        )

        max_lay_limit = int(df["Layovers"].max())
        max_lay = st.slider(
            "Layovers",
            0, max(max_lay_limit, 1), max_lay_limit,
            key=f"{key_prefix}_filter_max_lay",
        )

        selected_airlines = st.multiselect(
            "Airlines",
            options=sorted(df["Carrier"].unique()),
            default=list(df["Carrier"].unique()),
            key=f"{key_prefix}_filter_airlines",
        )

    with c_results:
        s_col1, s_col2, _ = st.columns([1, 1, 2])

        if s_col1.button(
            "💰 Cheapest",
            use_container_width=True,
            type="primary" if st.session_state.get(sort_by_key) == "Price" else "secondary",
            key=f"{key_prefix}_sort_price_btn",
        ):
            st.session_state[sort_by_key] = "Price"
            st.rerun()

        if s_col2.button(
            "⚡ Fastest",
            use_container_width=True,
            type="primary" if st.session_state.get(sort_by_key) == "Duration" else "secondary",
            key=f"{key_prefix}_sort_dur_btn",
        ):
            st.session_state[sort_by_key] = "Duration"
            st.rerun()

        df_filtered = df[
            (df["Price"] <= max_p) &
            (df["Duration"] <= pd.to_timedelta(max_dur, unit="h")) &
            (df["Layovers"] <= max_lay) &
            (df["Carrier"].isin(selected_airlines))
        ].sort_values(st.session_state.get(sort_by_key, "Price"))

        if df_filtered.empty:
            st.info("No flights match your current filter criteria. Try adjusting the price or duration sliders.")
            return

        st.caption(f"Showing {len(df_filtered)} of {len(df)} flights found")

        for _, row in df_filtered.iterrows():
            offer = flight_results["data"][int(row["idx"])]
            itineraries = offer["itineraries"]

            with st.container(border=True):
                for i, itin in enumerate(itineraries):
                    if i == 1:
                        st.markdown("---")

                    colA, colB = st.columns([3, 1])
                    with colA:
                        label = (
                            "🛫 Outbound" if len(itineraries) > 1 and i == 0
                            else ("🛬 Return" if i == 1 else "✈️ Flight")
                        )
                        segs = itin["segments"]
                        dep_time = datetime.datetime.fromisoformat(segs[0]["departure"]["at"].replace("Z", ""))

                        st.markdown(
                            f"**{label}** <span class='carrier-text'>{dep_time.strftime('%a, %d %b %Y')}</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"<span class='route-text'>{carriers.get(segs[0]['carrierCode'], 'N/A')} | "
                            f"{maps['city'].get(segs[0]['departure']['iataCode'])} → {maps['city'].get(segs[-1]['arrival']['iataCode'])}</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"⏱️ {format_duration(itin['duration'])} | 🔄 {len(segs)-1} Layovers",
                            unsafe_allow_html=True
                        )

                    # Price + book button only on first itinerary (outbound)
                    if i == 0:
                        with colB:
                            curr_map = {"EUR": "€", "USD": "$"}
                            sym = curr_map.get(str(row["Currency"]), str(row["Currency"]))
                            st.markdown(
                                f"<div class='price-text'>{sym}{row['Price']:.2f}</div>",
                                unsafe_allow_html=True
                            )

                            if st.button("Book Flight", key=f"{key_prefix}_bk_{int(row['idx'])}"):
                                token = amadeus.get_amadeus_access_token(amadeus_api_key, amadeus_api_secret)
                                price_res = amadeus.get_flight_price(token, offer)
                                if price_res and "data" in price_res:
                                    st.session_state.priced_offer = price_res["data"]["flightOffers"][0]
                                    # IMPORTANT: traveler counts stored for booking step
                                    st.session_state.traveler_counts = st.session_state.get(
                                        traveler_counts_key,
                                        {"ADULT": 1, "CHILD": 0, "INFANT": 0},
                                    )
                                    st.session_state.step = 8
                                    st.rerun()
                                else:
                                    st.error("Could not confirm price. Please select another flight!")

                    exp_label = (
                        "View Outbound Timeline" if len(itineraries) > 1 and i == 0
                        else ("View Return Timeline" if i == 1 else "View Full Timeline")
                    )

                    with st.expander(exp_label):
                        segments = itin["segments"]
                        for seg_idx, seg in enumerate(segments):
                            st.markdown(
                                f"""
                                <div class='timeline-row'>
                                    <span class='time-badge'>{seg['departure']['at'][-8:-3]}</span>
                                    <span>departing from <span class='city-name'>{maps['city'].get(seg['departure']['iataCode'])}</span>
                                    <span class='iata-code'>({seg['departure']['iataCode']})</span></span>
                                </div>
                                <div class='duration-info'>↓ Flight duration: {format_duration(seg['duration'])}</div>
                                <div class='timeline-row'>
                                    <span class='time-badge'>{seg['arrival']['at'][-8:-3]}</span>
                                    <span>arrival at <span class='city-name'>{maps['city'].get(seg['arrival']['iataCode'])}</span>
                                    <span class='iata-code'>({seg['arrival']['iataCode']})</span></span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            if seg_idx < len(segments) - 1:
                                next_seg = segments[seg_idx + 1]
                                arr_time = datetime.datetime.fromisoformat(seg["arrival"]["at"].replace("Z", ""))
                                dep_time2 = datetime.datetime.fromisoformat(next_seg["departure"]["at"].replace("Z", ""))
                                layover_td = dep_time2 - arr_time
                                hours, remainder = divmod(int(layover_td.total_seconds()), 3600)
                                minutes, _ = divmod(remainder, 60)
                                st.markdown(
                                    f"<div class='layover-info'>Layover: {hours}h {minutes}m</div>",
                                    unsafe_allow_html=True
                                )


def show_booking_step(
    *,
    amadeus,
    amadeus_api_key: str,
    amadeus_api_secret: str,
):
    """
    Step 7: Booking form + create order.
    Uses st.session_state.priced_offer and st.session_state.traveler_counts.
    """
    st.header("Confirm Your Booking")

    offer = st.session_state.priced_offer
    counts = st.session_state.get("traveler_counts", {"ADULT": 1, "CHILD": 0, "HELD_INFANT": 0})
    total_passengers = sum(counts.values())  # kept for parity (even if not shown)
    curr_map = {"EUR": "€", "USD": "$"}
    symbol = curr_map.get(offer["price"]["currency"], offer["price"]["currency"])
    st.write(f"Total Price: **{symbol}{offer['price']['total']}**")

    with st.form("traveler_form"):
        email = st.text_input("Contact Email Address")

        travelers = []
        idx = 1
        for p_type, count in counts.items():
            for _ in range(int(count)):
                st.subheader(f"Passenger {idx} ({p_type})")
                fn, ln, dob_col = st.columns([2, 2, 2])
                f_name = fn.text_input("First Name", key=f"fn_{idx}")
                l_name = ln.text_input("Last Name", key=f"ln_{idx}")
                d_o_b = dob_col.date_input(
                    "Date of Birth",
                    value=datetime.date(1990, 1, 1),
                    key=f"dob_{idx}",
                    min_value=datetime.date(1920, 1, 1),
                    max_value=datetime.date.today(),
                )

                travelers.append({
                    "id": str(idx),
                    "dateOfBirth": d_o_b.strftime("%Y-%m-%d"),
                    "name": {"firstName": f_name.upper(), "lastName": l_name.upper()},
                    "gender": "MALE",
                    "contact": {
                        "emailAddress": email if email else "traveler@example.com",
                        "phones": [{"deviceType": "MOBILE", "countryCallingCode": "1", "number": "123456789"}],
                    },
                })
                idx += 1

        if st.form_submit_button("Confirm & Book"):
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not email or not re.match(email_regex, email):
                st.error("🚨 Email Address is invalid")
            else:
                token = amadeus.get_amadeus_access_token(amadeus_api_key, amadeus_api_secret)
                booking_res = amadeus.create_flight_order(token, offer, travelers)

                if booking_res and "data" in booking_res:
                    st.session_state.confirmed_booking = booking_res
                    st.session_state.step = 9
                    st.rerun()
                else:
                    if booking_res and "errors" in booking_res:
                        for err in booking_res["errors"]:
                            detail = err.get("detail", "Unknown validation error")
                            pointer = err.get("source", {}).get("pointer", "")

                            match = re.search(r"travelers\[(\d+)\]|travelerPricings\[(\d+)\]", pointer)
                            if match:
                                idx_str = match.group(1) or match.group(2)
                                p_num = int(idx_str) + 1
                                if "lastName format is invalid" in detail:
                                    msg = f"Last Name of Passenger {p_num} is invalid"
                                elif "firstName format is invalid" in detail:
                                    msg = f"First Name of Passenger {p_num} is invalid"
                                elif "TOO_OLD" in detail:
                                    msg = f"Passenger {p_num} is too old"
                                else:
                                    msg = f"Passenger {p_num} Issue: {detail}"
                                st.error(f"🚨 {msg}")
                            elif "SEGMENT SELL FAILURE" in err.get("title", "") or err.get("code") == 34651:
                                st.error(
                                    "🚨 **Flight No Longer Available:** One or more segments of this flight sold out while you were "
                                    "filling out the form. Please go back and select a different flight."
                                )
                    else:
                        st.error("Booking failed. The flight may no longer be available or the connection timed out.")

    if st.button("← Back to Flight Results", use_container_width=True):
        st.session_state.step = 7
        st.rerun()


def show_confirmation_step(
    *,
    data_manager,
    calendar_client,
    google_client_id: str,
    google_client_secret: str,
    redirect_uri: str,
):
    """
    Step 8: Confirmation screen.
    Includes "Add to Google Calendar" which redirects to OAuth URL, storing offer+booking in state.
    """
    if "confirmed_booking" in st.session_state:
        st.balloons()
        st.success("🎉 Booking Confirmed!")
        pnr = st.session_state.confirmed_booking["data"]["associatedRecords"][0]["reference"]
        st.subheader(f"Booking Reference (PNR): {pnr}")
    else:
        st.error("No booking record found.")

    if st.session_state.get("google_creds"):
        st.success("✅ Flight added to your Google Calendar!")

    if not st.session_state.get("google_creds") and st.button("Add to Google Calendar 📅"):
        flow = calendar_client.get_google_flow(google_client_id, google_client_secret, redirect_uri)

        state_payload = {
            "offer": st.session_state.priced_offer,
            "booking": st.session_state.confirmed_booking,
        }
        state_data = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
        auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=state_data)

        st.session_state.google_auth_active = True
        # (you had this duplicated; keeping behavior identical)
        auth_url, _ = calendar_client.get_auth_url_and_state(flow, state=state_data)
        st.session_state.google_auth_active = True

        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()


def handle_google_oauth_callback(
    *,
    data_manager,
    calendar_client,
    google_client_id: str,
    google_client_secret: str,
    redirect_uri: str,
) -> None:
    """
    Call this ONCE near the top of main run_app().

    It checks st.query_params for OAuth callback (?code=...&state=...),
    stores creds, decodes state, reconstructs offer+booking into session_state,
    then creates calendar events and clears query params.
    """
    q = st.query_params
    if "code" not in q:
        return
    if "google_creds" in st.session_state:
        return

    flow = calendar_client.get_google_flow(google_client_id, google_client_secret, redirect_uri)
    st.session_state.google_creds = calendar_client.get_credentials_from_code(
        flow,
        q.get("state"),
        q.get("code"),
    )

    # state carries offer + booking
    state_decoded = json.loads(base64.urlsafe_b64decode(q["state"]).decode())
    offer = state_decoded.get("offer")
    booking = state_decoded.get("booking")

    st.session_state.priced_offer = offer
    st.session_state.confirmed_booking = booking

    maps = data_manager.get_iata_mappings()
    service = calendar_client.get_calendar_service(st.session_state.google_creds)

    events_to_create = []
    for itin in offer["itineraries"]:
        seg = itin["segments"]
        events_to_create.append({
            "summary": f"Flight: {maps['city'].get(seg[0]['departure']['iataCode'])} to {maps['city'].get(seg[-1]['arrival']['iataCode'])}",
            "start_time": datetime.datetime.fromisoformat(seg[0]["departure"]["at"].replace("Z", "")),
            "end_time": datetime.datetime.fromisoformat(seg[-1]["arrival"]["at"].replace("Z", "")),
            "origin": maps["city"].get(seg[0]["departure"]["iataCode"]),
            "destination": maps["city"].get(seg[-1]["arrival"]["iataCode"]),
            "start_tz": maps["tz"].get(seg[0]["departure"]["iataCode"], "UTC"),
            "end_tz": maps["tz"].get(seg[-1]["arrival"]["iataCode"], "UTC"),
        })

    calendar_client.create_calendar_events_batch(service, events_to_create)

    # Clear query params and go to confirmation step
    st.query_params.clear()
    st.session_state.step = 8
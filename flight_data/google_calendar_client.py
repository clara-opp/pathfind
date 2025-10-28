import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_google_flow(client_id, client_secret, redirect_uri):
    """Creates and returns a Google OAuth Flow object."""
     # This dictionary structure is what the Flow object expects.
    # It mimics the structure of the credentials.json file.
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    return Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=redirect_uri
    )

def get_auth_url_and_state(flow, state=None):
    """Generates the authorization URL and state for the user to click."""
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state
    )
    return authorization_url, state

def get_credentials_from_code(flow, state, code):
    """
    Exchanges the authorization code for credentials (access/refresh tokens).
    """
    flow.fetch_token(code=code)
    return flow.credentials

def get_calendar_service(credentials):
    """Builds and returns the calendar service object from credentials."""
    try:
        service = build("calendar", "v3", credentials=credentials)
        return service
    except HttpError as error:
        print(f"An error occurred building the calendar service: {error}")
        return None

def create_calendar_event(service, summary, start_time, end_time, origin, destination, start_tz, end_tz):
    """Creates an event on the user's primary calendar."""
    # DEBUG: Check if this function is ever called and what data it receives.
    print(f"DEBUG: Attempting to create calendar event: {summary} from {start_time} to {end_time}")
    event = {
        "summary": summary,
        "location": origin,
        "description": f"Flight from {origin} to {destination}",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": start_tz,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": end_tz,
        },
    }
    try:
        created_event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"Event created successfully! View it here: {created_event.get('htmlLink')}")
        return True
    except HttpError as error:
        print(f"An error occurred creating the calendar event: {error}")
        return False
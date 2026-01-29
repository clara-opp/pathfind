# Pathfind travel dashboard

## Repository structure

The complete Streamlit application lives inside the `database/` directory.

- `database/travel_planner.py`  
  Main entry point of the app (final Streamlit file). Start the application from here.

- `database/modules/`  
  Contains the individual feature modules that are imported and orchestrated by `travel_planner.py`. This keeps the codebase modular and makes it easier to maintain/extend.

- `database/personas/`  
  Static assets used by the app, especially images (e.g., persona visuals).

- `database/database_final.py`
  Script that automatically builds our whole database, based on all relevant files in the `database/data/` folder.

- `database/run_update_database.bat`
  Script within automized scheduling process, that updates relevant data scources once per day.

## Environment variables (.env)

To run the app successfully, create a `.env` file (e.g., in the project root) and provide the following keys:

```dotenv
AMADEUS_API_KEY=""
AMADEUS_API_SECRET=""
OPENAI_API_KEY=""
ROXY_API_KEY=""
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GOOGLE_MAPS_API_KEY=""
SERPER_API_KEY=""
TRAVEL_BUDDY_API_KEY=""
```

## Login
The app includes a login page that is enabled by default. To access the dashboard, add at least one valid login pair to your .env file using the format:
LOGIN_USER="password"
If you want to disable the login step for local testing, comment out the require_login() call in the run_app() function (in database/travel_planner.py).

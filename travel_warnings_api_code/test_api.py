from tugo_api import collect_travel_warnings
import pprint

rows = collect_travel_warnings(limit=1)   # fetch up to 5 items from the API
pprint.pprint(rows[:3])

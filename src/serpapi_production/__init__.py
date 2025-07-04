import os
import serpapi
from mongo_wrapper.mongo_wrapper import MongoWrapper
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

MONGO_IP       = os.getenv("MONGO_IP")
MONGO_PORT     = os.getenv("MONGO_PORT")
MONGO_DB       = "serpapi_5y"
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
SERPAPI_KEY    = os.getenv("SERPAPI_API_KEY")

mongo_client = MongoWrapper(
    db=MONGO_DB,
    user=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    ip=MONGO_IP,
    port=MONGO_PORT
)

def _save_timeseries(data: Dict, keyword_set: str, state: str) -> None:
    coll = f"serpapi_timeseries_{state}_{keyword_set}"
    mongo_client.save_new_serpapi_search(collection=coll, data=data)

def _fetch_timeseries(keyword_set: str, state: str) -> Dict:
    params = {
        "engine":    "google_trends",
        "q":         keyword_set,
        "data_type": "TIMESERIES",
        "hl":        "es",
        "geo":       state,
        "date":      "all",
        "api_key":   SERPAPI_KEY
    }
    resp = serpapi.search(params)
    return dict(resp.data)

def fetch_timeseries_data(
    keyword_sets: List[str],
    states:       List[str]
) -> None:
    existing = set(mongo_client.get_all_collections())
    total = len(keyword_sets) * len(states)
    count = 0

    for q in keyword_sets:
        for state in states:
            coll = f"serpapi_timeseries_{state}_{q}"
            if coll in existing:
                count += 1
                continue
            try:
                data = _fetch_timeseries(q, state)
                _save_timeseries(data, q, state)
            except Exception as e:
                print(f"[fetch_timeseries_data] Error for ({state}, '{q}'): {e}")
            count += 1
            print(f"Progress: {count}/{total} — state={state}, q='{q}'")

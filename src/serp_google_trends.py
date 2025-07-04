import requests
import serpapi

from mongo_wrapper.mongo_wrapper import MongoWrapper

import os
from dotenv import load_dotenv

load_dotenv()

MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = "serpapi_5y"
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

mongo_client = MongoWrapper(
    db=MONGO_DB,
    user=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    ip=MONGO_IP,
    port=MONGO_PORT
)

STATES = [
    "MX-AGU",
    "MX-BCN",
    "MX-BCS",
    "MX-CAM",
    "MX-CHP",
    "MX-CHH",
    "MX-COA",
    "MX-COL",
    "MX-DUR",
    "MX-GUA",
    "MX-GRO",
    "MX-HID",
    "MX-JAL",
    "MX-DIF",
    "MX-MIC",
    "MX-MOR",
    "MX-NAY",
    "MX-NLE",
    "MX-OAX",
    "MX-PUE",
    "MX-QUE",
    "MX-ROO",
    "MX-SLP",
    "MX-SIN",
    "MX-SON",
    "MX-MEX",
    "MX-TAB",
    "MX-TAM",
    "MX-TLA",
    "MX-VER",
    "MX-YUC",
    "MX-ZAC"
]

def save_data(params: dict[str, str], data: dict, data_type: str, state: str = None) -> None:
    collection_name = f"serpapi_{data_type}_{params['q']}" if state is None else f"serpapi_{data_type}_{state}_{params['q']}"

    mongo_client.save_new_serpapi_search(collection=collection_name, data=data)

def get_data(params: dict[str, str]) -> dict:
    serpapi_response = serpapi.search(params)

    return dict(serpapi_response.data)

def main():
    keywords = [
        "agua potable, FOVISSSTE"
    ]

    for index_k, keyword_set in enumerate(keywords):
        params_geo = {
            "engine": "google_trends",
            "q": keyword_set,
            "data_type": "GEO_MAP",
            "hl": "es",
            "geo": "MX",
            "date": "all",
            "region": "REGION",
            "api_key": SERPAPI_API_KEY
        }

        collection_name = f'serpapi_geo_{keyword_set}'
        if collection_name in mongo_client.get_all_collections():
            print(f'Collection {collection_name} already exists. Skipping...')

            pass

        try:
            geo_data = get_data(params_geo)

            save_data(params_geo, geo_data, "geo")
        except Exception as e:
            print(f'Error fetching geo data for keyword "{keyword_set}": {e}')

            pass 

        # for index, state in enumerate(STATES):
        #     params_timeseries = {
        #         "engine": "google_trends",
        #         "q": keyword_set,
        #         "data_type": "TIMESERIES",
        #         "hl": "es",
        #         "geo": state,
        #         "date": "all",
        #         "api_key": SERPAPI_API_KEY
        #     }

        #     collection_name = f'serpapi_timeseries_{state}_{keyword_set}'
        #     if collection_name in mongo_client.get_all_collections():
        #         print(f'Collection {collection_name} already exists. Skipping...')

        #         continue
            
        #     try:
        #         timeseries_data = get_data(params_timeseries)
        #     except Exception as e:
        #         print(f'Error fetching timeseries data for state {state} with keyword "{keyword_set}": {e}')
        #         continue

        #     save_data(params_timeseries, timeseries_data, "timeseries", state)

        #     print(f'State {index + 1} / {len(STATES)}: {state}')

        print(f'{index_k + 1} / {len(keywords)}')

if __name__ == "__main__":
    main()
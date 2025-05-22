import requests
import serpapi

from mongo_wrapper.mongo_wrapper import MongoWrapper

import os
from dotenv import load_dotenv

load_dotenv()

MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = "serpapi"
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

def save_data(params: dict[str, str], data: dict) -> None:
    collection_name = f"serpapi_{params['q']}"

    mongo_client.save_new_serpapi_search(collection=collection_name, data=data)

def get_data(params: dict[str, str]) -> dict:
    serpapi_response = serpapi.search(params)

    return dict(serpapi_response.data)

def main():
    keywords = [
        "crisis,desempleo,pobreza,conflictos,discriminación",
        "violencia,becas,escuela secundaria,enfermedad,centro de salud",
        "pensiones,seguro social,ayuda alimentaria,banco de alimentos,comedor comunitario",
        "comida barata,receta pobre,apoyo Infonavit,ayuda renta,renta barata",
        "servicios en la vivienda,vivienda del gobierno"
    ]

    for index, keyword_set in enumerate(keywords):
        params = {
            "engine": "google_trends",
            "q": keyword_set,
            "data_type": "GEO_MAP",
            "hl": "es",
            "geo": "MX",
            "region": "REGION",
            "api_key": SERPAPI_API_KEY
        }

        data = get_data(params)

        save_data(params, data)

        print(f'{index + 1} / {len(keywords)}')

if __name__ == "__main__":
    main()
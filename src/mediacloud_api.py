import mediacloud.api
from datetime import date
from time import sleep

from mongo_wrapper.mongo_wrapper import MongoWrapper

import os
from dotenv import load_dotenv

load_dotenv()

MEDIACLOUD_API_KEY = os.getenv("MEDIA_CLOUD_API_KEY")
COLLECTIONS = [
    38380322,
    38380323,
    38380325,
    38380327,
    38380331,
    38380338,
    38380342,
    38380344,
    38380346,
    38380348,
    38380350,
    38380353,
    38380354,
    38380356,
    38380358,
    38380360,
    38380362,
    38380364,
    38380366,
    38380368,
    38380370,
    38380372,
    38380374,
    38380377,
    38380379,
    38380381,
    38380383,
    38380385,
    38380387,
    38380389,
    38380391,
    38380393
]

MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = "news_outlets"
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

mongo_client = MongoWrapper(
    db=MONGO_DB,
    user=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    ip=MONGO_IP,
    port=MONGO_PORT
)

def fetch_new_articles(mediacloud_engine: mediacloud.api.SearchApi, keyword: str, start_date: date, end_date: date, pagination_token: str = "initial") -> list[list[dict], str]: 
    if pagination_token == "initial":
        pagination_token = None
    elif pagination_token is None:
        return None, None
    
    page, pagination_token = mediacloud_engine.story_list(query=keyword, collection_ids=COLLECTIONS, start_date=start_date, end_date=end_date, pagination_token=pagination_token)

    return page, pagination_token

def get_data(mediacloud_engine: mediacloud.api.SearchApi, keyword: str, start_date: date, end_date: date):
    articles_num = 0

    pagination_token = "initial"
    fails = 0

    while pagination_token is not None and fails < 5:
        try:
            new_articles, pagination_token = fetch_new_articles(mediacloud_engine, keyword, start_date, end_date, pagination_token)
            if new_articles is None:
                print(f'Got {articles_num} in total')

                break

            mongo_client.save_new_pagination_news(news=new_articles, collection_name=f'mediacloud_{keyword}')

            articles_num += len(new_articles)

            print(f'Got {len(new_articles)} new articles. Total: {articles_num}')

            fails = 0

            sleep(5)
        except Exception as e:
            fails += 1
            print(f'Error: {e}. Fails: {fails}')

def main():
    mc_search = mediacloud.api.SearchApi(MEDIACLOUD_API_KEY)

    get_data(mc_search, "desempleo", date(2020, 1, 1), date(2022, 12, 1))
    

if __name__ == "__main__":
    main()
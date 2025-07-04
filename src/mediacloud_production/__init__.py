import os
import time
from datetime import date
import mediacloud.api
from mongo_wrapper.mongo_wrapper import MongoWrapper
from dotenv import load_dotenv
from typing import List, Optional, Tuple

load_dotenv()

MONGO_IP       = os.getenv("MONGO_IP")
MONGO_PORT     = os.getenv("MONGO_PORT")
MONGO_DB       = "news_outlets"
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

COLLECTION_IDS = [
    38380322, 38380323, 38380325, 38380327, 38380331, 38380338,
    38380342, 38380344, 38380346, 38380348, 38380350, 38380353,
    38380354, 38380356, 38380358, 38380360, 38380362, 38380364,
    38380366, 38380368, 38380370, 38380372, 38380374, 38380377,
    38380379, 38380381, 38380383, 38380385, 38380387, 38380389,
    38380391, 38380393
]

MEDIACLOUD_API_KEY = os.getenv("MEDIA_CLOUD_API_KEY")

mongo_client = MongoWrapper(
    db=MONGO_DB,
    user=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    ip=MONGO_IP,
    port=MONGO_PORT
)

mc_api = mediacloud.api.SearchApi(MEDIACLOUD_API_KEY)

def _fetch_page(
    keyword: str,
    start_date: date,
    end_date: date,
    pagination_token: Optional[str]
) -> Tuple[List[dict], Optional[str]]:
    page, next_token = mc_api.story_list(
        query=keyword,
        collection_ids=COLLECTION_IDS,
        start_date=start_date,
        end_date=end_date,
        pagination_token=(None if pagination_token == "initial" else pagination_token)
    )
    return page, next_token


def fetch_news_data(
    keywords: List[str],
    start_date: date,
    end_date: date,
    sleep_between_requests: float = 5.0,
    max_retries: int = 5
) -> None:
    existing = set(mongo_client.get_all_collections())
    total = len(keywords)
    
    for idx, kw in enumerate(keywords, 1):
        coll_name = f"mediacloud_{kw}"
        if coll_name in existing:
            print(f"[{idx}/{total}] Collection {coll_name} exists, skipping.")
            continue

        print(f"[{idx}/{total}] Fetching news for '{kw}'...")
        token = "initial"
        retries = 0
        count = 0

        while token is not None and retries < max_retries:
            try:
                articles, token = _fetch_page(kw, start_date, end_date, token)
                if not articles:
                    break
                mongo_client.save_new_pagination_news(news=articles, collection_name=coll_name)
                count += len(articles)
                print(f"  → got {len(articles)} articles (total {count})")
                retries = 0
                time.sleep(sleep_between_requests)
            except Exception as e:
                retries += 1
                print(f"  !! error: {e} (retry {retries}/{max_retries})")
        print(f"[{idx}/{total}] Done '{kw}' ({count} articles)\n")

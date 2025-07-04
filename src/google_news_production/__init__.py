# gnews_production.py

import os
import time
from datetime import datetime, timedelta, date
from hashlib import sha256
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict

from gnews import GNews
from mongo_wrapper.mongo_wrapper import MongoWrapper
from logger.logger import Logger
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MONGO_IP       = os.getenv("MONGO_IP")
MONGO_PORT     = os.getenv("MONGO_PORT")
MONGO_DB       = "news_outlets_final"
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

mongo_client = MongoWrapper(
    db=MONGO_DB,
    user=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    ip=MONGO_IP,
    port=MONGO_PORT
)

fetch_logger = Logger(logger_type="gnews_fetcher", stream_handler=True)

proxies_path = Path(__file__).parent / "files/proxies.txt"
def _load_proxies() -> cycle:
    if not proxies_path.exists():
        return cycle([None])
    with open(proxies_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    formatted = [l if l.startswith("http") else f"http://{l}" for l in lines]
    return cycle(formatted)

_proxy_cycle = _load_proxies()

def _hash_url(url: str) -> str:
    return sha256(url.encode("utf-8")).hexdigest()

def _fetch_range(
    engine: GNews,
    keyword: str,
    start: datetime,
    end: datetime,
    proxy: str
) -> List[Dict]:
    engine.start_date = (start.year, start.month, start.day)
    engine.end_date   = (end.year, end.month, end.day)
    engine.country    = "mx"
    engine.language   = "es"
    engine.max_results= 100
    if proxy:
        engine.proxies = {"http": proxy, "https": proxy}

    try:
        raw = engine.get_news(keyword)
        articles = []
        for item in raw:
            item["id"] = _hash_url(item.get("url", "")) 
            articles.append(item)
        return articles
    except Exception as e:
        fetch_logger.log(f"[{keyword}] Error {start.date()}–{end.date()}: {e}", "error")
        return []

def fetch_gnews_data(
    keywords: List[str],
    start_date: date,
    end_date:   date,
    max_workers: int = 5,
    chunk_days: int = 10,
    sleep_between: float = 1.0
) -> None:
    total = len(keywords)
    for idx, kw in enumerate(keywords, 1):
        coll_name = f"gnews_{kw}"
        fetch_logger.log(f"[{idx}/{total}] Start '{kw}'", "info")
        engine = GNews()

        intervals: List[Tuple[datetime, datetime]] = []
        cur = datetime(start_date.year, start_date.month, start_date.day)
        last = datetime(end_date.year, end_date.month, end_date.day)
        delta = timedelta(days=chunk_days)
        while cur < last:
            nxt = min(cur + delta, last)
            intervals.append((cur, nxt))
            cur = nxt

        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = {
                exe.submit(_fetch_range, engine, kw, s, e, next(_proxy_cycle)): (s, e)
                for s, e in intervals
            }
            count = 0
            for fut in as_completed(futures):
                start_i, end_i = futures[fut]
                articles = fut.result()
                if articles:
                    try:
                        mongo_client.save_new_pagination_news(
                            news=articles,
                            collection_name=coll_name
                        )
                        count += len(articles)
                        fetch_logger.log(f"  → {len(articles)} [{start_i.date()}–{end_i.date()}] (total {count})", "info")
                    except Exception as db_e:
                        fetch_logger.log(f"  !! DB error: {db_e}", "error")
                else:
                    fetch_logger.log(f"  → 0 articles [{start_i.date()}–{end_i.date()}]", "info")
                time.sleep(sleep_between)

        fetch_logger.log(f"[{idx}/{total}] Done '{kw}' (fetched {count})", "info")

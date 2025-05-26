from gnews import GNews
from datetime import datetime, timedelta
from time import sleep
from hashlib import sha256
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from mongo_wrapper.mongo_wrapper import MongoWrapper
from logger.logger import Logger

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
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

# Logger
fetch_logger = Logger(logger_type="news_fetcher", stream_handler=True)

# Proxy setup
proxies_path = Path(__file__).parent / "files/proxies.txt"
def get_proxies() -> list[str]:
    with open(proxies_path) as f:
        return [line.strip() if line.strip().startswith("http") else f'http://{line.strip()}'
                for line in f if line.strip()]

proxies = get_proxies()
proxy_cycle = cycle(proxies)

# Utility functions
def hash_url(url: str) -> str:
    return sha256(url.encode('utf-8')).hexdigest()

# Fetch articles for a given date range and return list of dicts
# Uses a proxy to route requests
def fetch_articles_range(gnews_engine: GNews, keyword: str, start: datetime, end: datetime, proxy: str) -> list[dict]:
    gnews_engine.start_date = (start.year, start.month, start.day)
    gnews_engine.end_date = (end.year, end.month, end.day)
    gnews_engine.country = "mx"
    gnews_engine.language = "es"
    gnews_engine.max_results = 100

    try:
        gnews_engine.proxies = {"http": proxy, "https": proxy}
        raw = gnews_engine.get_news(keyword)
        articles = []
        for item in raw:
            item["id"] = hash_url(item.get("url", ""))
            articles.append(item)
        return articles
    except Exception as e:
        fetch_logger.log(f"Error fetching {keyword} {start.date()}–{end.date()}: {e}", "error")
        return []

# Process one state: split into chunks and fetch each concurrently
def process_state(state: str, start_date: datetime, end_date: datetime, max_workers: int = 5) -> None:
    fetch_logger.log(f"Starting fetch for {state}", "info")
    gnews_engine = GNews()
    # Build date chunks of 10 days
    delta = timedelta(days=10)
    ranges = []
    cur = start_date
    while cur < end_date:
        nxt = min(cur + delta, end_date)
        ranges.append((cur, nxt))
        cur = nxt

    # Prepare tasks
    tasks = []
    for r in ranges:
        tasks.append((state, *r))

    # Use ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for state, s, e in tasks:
            proxy = next(proxy_cycle)
            futures[executor.submit(fetch_articles_range, gnews_engine, state, s, e, proxy)] = (state, s, e)

        for future in tqdm(as_completed(futures), total=len(futures), desc=state):
            st, s, e = futures[future]
            articles = future.result()
            if articles:
                fetch_logger.log(f"Fetched {len(articles)} for {st} {s.date()}–{e.date()}", "info")
                coll = f"gnews_{st}"
                try:
                    mongo_client.save_new_pagination_news(news=articles, collection_name=coll)
                except Exception as dbe:
                    fetch_logger.log(f"DB save error for {st} {s.date()}–{e.date()}: {dbe}", "error")
            else:
                fetch_logger.log(f"No articles for {st} {s.date()}–{e.date()}", "info")
            sleep(1)

# Main execution
def main():
    states = [
        "Aguascalientes",
        "Baja California Sur",
        "Campeche",
        "Coahuila",
        "Colima",
        "Nayarit",
        "Sinaloa",
        "Tabasco",
        "Tlaxcala",
        "Zacatecas"
    ]
    for state in states:
        process_state(
            state,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 1),
            max_workers=25
        )

if __name__ == "__main__":
    main()

# gnews_decoder_production.py

import os
import time
from pathlib import Path
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from tqdm import tqdm
from googlenewsdecoder import gnewsdecoder
from mongo_wrapper.mongo_wrapper import MongoWrapper
from logger.logger import Logger
from dotenv import load_dotenv

load_dotenv()

mongo_client = MongoWrapper(
    db="news_outlets_final",
    user=os.getenv("MONGO_USERNAME"),
    password=os.getenv("MONGO_PASSWORD"),
    ip=os.getenv("MONGO_IP"),
    port=os.getenv("MONGO_PORT")
)

decoder_logger = Logger(logger_type="url_decoder", stream_handler=False)

_proxies_file = Path(__file__).parent / "files/proxies.txt"
def _load_proxies() -> cycle:
    if not _proxies_file.exists():
        return cycle([None])
    with open(_proxies_file) as f:
        lines = [l.strip() for l in f if l.strip()]
    formatted = [l if l.startswith("http") else f"http://{l}" for l in lines]
    return cycle(formatted)

_proxy_cycle = _load_proxies()

def _decode_url(url: str, proxy: Optional[str]) -> Optional[str]:
    for attempt in range(1, 6):
        try:
            result = gnewsdecoder(url, proxy=proxy)
            if result and result.get("decoded_url"):
                return result["decoded_url"]
            decoder_logger.log(f"No decoded_url on attempt {attempt} for {url}", "error")
        except Exception as e:
            decoder_logger.log(f"Error on attempt {attempt} for {url}: {e}", "error")
        time.sleep(0.1)
    return None

def _process_one(article: dict) -> None:
    if article.get("decoded_url"):
        return

    proxy = next(_proxy_cycle)
    decoded = _decode_url(article["url"], proxy)
    if not decoded:
        return

    try:
        mongo_client.update_collection_entries(
            article["__collection_name"],
            [{"_id": article["_id"], "update_data": {"decoded_url": decoded}}]
        )
        decoder_logger.log(f"Updated {_[:30]}… → {decoded[:30]}…", "info")
    except Exception as e:
        decoder_logger.log(f"DB update failed for {article['_id']}: {e}", "error")

def _update_collection(
    collection: str,
    articles: List[dict],
    max_workers: int
) -> None:
    for art in articles:
        art["__collection_name"] = collection

    decoder_logger.log(f"Decoding {len(articles)} urls in {collection}", "info")
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        futures = {exe.submit(_process_one, art): art for art in articles}
        for _ in tqdm(as_completed(futures), total=len(futures), desc=collection):
            pass
    decoder_logger.log(f"Finished {collection}", "info")

def decode_gnews_links(
    states: List[str],
    max_workers: int = 20
) -> None:
    for state in states:
        coll = f"gnews_{state}"
        articles = mongo_client.get_collection_entries(coll) or []
        if not articles:
            decoder_logger.log(f"No articles in {coll}", "info")
            continue
        _update_collection(coll, articles, max_workers)

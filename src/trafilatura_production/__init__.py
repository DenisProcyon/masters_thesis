# gnews_content_production.py

import os
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import trafilatura
from mongo_wrapper.mongo_wrapper import MongoWrapper
from dotenv import load_dotenv

load_dotenv()

def _make_mongo_client() -> MongoWrapper:
    return MongoWrapper(
        db="news_outlets",
        user=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        ip=os.getenv("MONGO_IP"),
        port=os.getenv("MONGO_PORT"),
    )

def _fetch_content(url: str) -> Optional[str]:
    html = trafilatura.fetch_url(url)
    if not html:
        return None
    return trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
        output_format="txt",
    )

def _process_and_update(
    article: Dict,
    collection: str,
    mongo_client: MongoWrapper
) -> None:
    if article.get("content"):
        return
    url = article.get("decoded_url") or article.get("url")
    text = _fetch_content(url)
    if not text:
        return
    mongo_client.update_collection_entries(
        collection,
        [{"_id": article["_id"], "update_data": {"content": text}}]
    )

def fetch_and_store_contents(
    states: List[str],
    max_workers: int = 10
) -> None:
    client = _make_mongo_client()
    for state in states:
        coll = f"gnews_{state}"
        articles = client.get_collection_entries(coll) or []
        to_process = [a for a in articles if not a.get("content")]
        if not to_process:
            continue

        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = {
                exe.submit(_process_and_update, art, coll, client): art
                for art in to_process
            }
            for _ in tqdm(as_completed(futures), total=len(futures),
                          desc=f"Extracting content for {state}", unit="article"):
                pass

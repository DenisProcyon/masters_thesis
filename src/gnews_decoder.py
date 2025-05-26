import random
from time import sleep
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from googlenewsdecoder import gnewsdecoder
from mongo_wrapper.mongo_wrapper import MongoWrapper
from logger.logger import Logger

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths and environment
proxies_path = Path(__file__).parent / "files/proxies.txt"

# Initialize MongoDB client
mongo_client = MongoWrapper(
    db="news_outlets",
    user=os.getenv("MONGO_USERNAME"),
    password=os.getenv("MONGO_PASSWORD"),
    ip=os.getenv("MONGO_IP"),
    port=os.getenv("MONGO_PORT")
)

# Initialize logger
debug_logger = Logger(logger_type="url_decoder", stream_handler=False)

# Read proxies from file and cycle through them
def get_proxies() -> list[str]:
    with open(proxies_path) as file:
        lines = [line.strip() for line in file if line.strip()]
    return [proxy if proxy.startswith("http") else f'http://{proxy}' for proxy in lines]

proxies = get_proxies()
proxy_cycle = cycle(proxies)

# Decode a single URL with retry logic
def decode_url(url: str, proxy: str) -> str | None:
    attempts = 5
    for attempt in range(1, attempts + 1):
        try:
            result = gnewsdecoder(url, proxy=proxy)
            if result and result.get("decoded_url"):
                decoded = result["decoded_url"]
                debug_logger.log(f"[{proxy}] Decoded {url[:30]}... to {decoded[:30]}...", "info")
                return decoded
            else:
                debug_logger.log(f"[{proxy}] No result on attempt {attempt} for {url}", "error")
        except Exception as e:
            debug_logger.log(f"[{proxy}] Error decoding {url} on attempt {attempt}: {e}", "error")
        sleep(0.1)
    return None

# Worker function to decode and update a single article
def process_article(article: dict) -> None:
    if article.get("decoded_url"):
        return

    proxy = next(proxy_cycle)
    decoded = decode_url(article["url"], proxy)
    if decoded:
        try:
            mongo_client.update_collection_entries(
                article['__collection_name'],
                [{"_id": article["_id"], "update_data": {"decoded_url": decoded}}]
            )
            debug_logger.log(f"Updated article ID {article['_id']}", "info")
        except Exception as e:
            debug_logger.log(f"Failed to update DB for {article['_id']}: {e}", "error")

# Multithreaded update with progress bar per collection/state
def update_articles_multithread(collection: str, articles: list[dict], max_workers: int = 10) -> None:
    # Attach collection name so each worker knows where to update
    for art in articles:
        art['__collection_name'] = collection

    debug_logger.log(f"Start processing collection {collection} with {len(articles)} articles", "info")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_article, art): art for art in articles}
        # Show one tqdm progress bar per collection
        for _ in tqdm(as_completed(futures), total=len(futures), desc=f"{collection}"):
            pass
    debug_logger.log(f"Finished processing collection {collection}", "info")

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
        debug_logger.log(f"Processing state '{state}'...", "info")
        collection_name = f"gnews_{state}"
        articles = mongo_client.get_collection_entries(collection_name)
        if not articles:
            debug_logger.log(f"No articles found in {collection_name}", "info")
            continue

        update_articles_multithread(collection_name, articles, max_workers=50)

if __name__ == "__main__":
    main()

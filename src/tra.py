import os
from dotenv import load_dotenv
from itertools import islice
from typing import Iterable, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura
from tqdm import tqdm

from mongo_wrapper.mongo_wrapper import MongoWrapper

def chunked(iterable: Iterable, size: int) -> Iterable[List]:
    it = iter(iterable)
    while chunk := list(islice(it, size)):
        yield chunk

def fetch_article_content(url: str) -> str | None:
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

def process_and_update(art: Dict, mongo_client: MongoWrapper, collection: str) -> None:
    """
    Для одного документа: скачиваем, парсим и сразу пишем в Mongo.
    """
    try:
        text = fetch_article_content(art["url"])
    except Exception as e:
        print(f"Error fetching {art['url']}: {e}")
        return

    if text:
        mongo_client.update_collection_entries(
            collection,
            [{"_id": art["_id"], "update_data": {"content": text}}]
        )

def get_articles_content_threaded(
    articles: List[Dict],
    mongo_client: MongoWrapper,
    collection: str,
    max_workers: int = 10,
) -> List[Dict]:
    to_process = [a for a in articles if not a.get("content")]
    total = len(to_process)
    if total == 0:
        return articles

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_and_update, art, mongo_client, collection): art
            for art in to_process
        }

        for _ in tqdm(as_completed(futures), total=total, desc="Processing articles", unit="article"):
            try:
                _.result()
            except Exception as e:
                art = futures[_]
                print(f"Failed {art['url']}: {e}")

    return articles

def main() -> None:
    load_dotenv()

    mongo_client = MongoWrapper(
        db="news_outlets",
        user=os.getenv("MONGO_USERNAME"),
        password=os.getenv("MONGO_PASSWORD"),
        ip=os.getenv("MONGO_IP"),
        port=os.getenv("MONGO_PORT"),
    )

    states = [
        "Chiapas", "Chihuahua", "Coahuila", "Colima", "Durango", "Guerrero",
        "Hidalgo", "Jalisco", "Mexico", "Michoacan", "Morelos", "Nayarit",
        "Nuevo Leon", "Oaxaca", "Puebla", "Queretaro", "Quintana Roo",
        "San Luis Potosi", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas",
        "Tlaxcala", "Veracruz", "Yucatan", "Ciudad de México", "Zacatecas"
    ]

    for state in states:
        print(f'Processing {state}...')
        articles = mongo_client.get_collection_entries(f'mediacloud_{state}')
        get_articles_content_threaded(
            articles,
            mongo_client,
            f'mediacloud_{state}',
            max_workers=50  # настройте по возможностям вашей машины и сети
        )

if __name__ == "__main__":
    main()

import os
import multiprocessing
from dotenv import load_dotenv
from itertools import islice
from typing import Iterable, List, Dict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

import trafilatura
from tqdm import tqdm

from mongo_wrapper.mongo_wrapper import MongoWrapper

# Принудительно ставим метод spawn для подпроцессов
multiprocessing.set_start_method("spawn", force=True)

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
    try:
        text = fetch_article_content(art["decoded_url"])
        if text:
            mongo_client.update_collection_entries(
                collection,
                [{"_id": art["_id"], "update_data": {"content": text}}]
            )
    except Exception as e:
        # Любые ошибки «гасим» здесь
        print(f"[{collection}] Error fetching {art['decoded_url']}: {e}")

def get_articles_content_threaded(
    articles: List[Dict],
    mongo_client: MongoWrapper,
    collection: str,
    max_workers: int = 10,
) -> None:
    to_process = [a for a in articles if not a.get("content")]
    if not to_process:
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_and_update, art, mongo_client, collection): art
            for art in to_process
        }
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Processing {collection}",
            unit="article"
        ):
            # Здесь мы можем логировать неудачные futures, 
            # но исключения внутри уже пойманы в process_and_update
            if future.exception():
                art = futures[future]
                print(f"[{collection}] Future error on {art['decoded_url']}: {future.exception()}")

def process_state(state: str) -> None:
    try:
        load_dotenv()  # подгружаем переменные в каждом подпроцессе
        mongo_client = MongoWrapper(
            db="news_outlets",
            user=os.getenv("MONGO_USERNAME"),
            password=os.getenv("MONGO_PASSWORD"),
            ip=os.getenv("MONGO_IP"),
            port=os.getenv("MONGO_PORT"),
        )
        coll = f"gnews_{state}"
        print(f"=== Start {state} (pid={os.getpid()}) ===")
        articles = mongo_client.get_collection_entries(coll)
        get_articles_content_threaded(articles, mongo_client, coll, max_workers=50)
        print(f"=== Done {state} ===")
    except Exception as e:
        # Любая фатальная ошибка в рамках state не убьёт весь pool
        print(f"[process_state:{state}] Fatal error: {e}")

def main() -> None:
    states = [
        "Chiapas", "Chihuahua", "Coahuila", "Colima", "Durango",
        "Guerrero", "Hidalgo", "Jalisco", "Mexico", "Michoacan",
        "Morelos", "Nayarit", "Nuevo Leon", "Oaxaca", "Puebla",
        "Queretaro", "Quintana Roo", "San Luis Potosi", "Sinaloa",
        "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz",
        "Yucatan", "Ciudad de México", "Zacatecas", "Aguascalientes",
        "Baja California", "Baja California Sur", "Campeche", "Guanajuato"
    ]

    # Указываем контекст spawn, чтобы ProcessPoolExecutor тоже создавал spawn-процессы
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=10, mp_context=ctx) as proc_pool:
        futures = {proc_pool.submit(process_state, st): st for st in states}
        for future in as_completed(futures):
            st = futures[future]
            if exc := future.exception():
                print(f"[Main] State {st} crashed: {exc}")

if __name__ == "__main__":
    main()

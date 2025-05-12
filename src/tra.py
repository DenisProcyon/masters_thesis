import os
from dotenv import load_dotenv
from itertools import islice
from typing import Iterable, List, Dict

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

def get_articles_content(
    articles: List[Dict],
    mongo_client: MongoWrapper,
    collection: str,
    batch_size: int = 10,
) -> List[Dict]:
    to_process = [a for a in articles if not a.get("content")]
    total = len(to_process)
    if total == 0:
        return articles

    with tqdm(total=total, desc="Processing articles", unit="article") as pbar:
        for batch in chunked(to_process, batch_size):
            for art in batch:
                try:
                    art["content"] = fetch_article_content(art["url"])
                except Exception as e:
                    print(f"Cannot download {art['url']}: {e}")

            batch_updates = [
                {"_id": art["_id"], "update_data": {"content": art["content"]}}
                for art in batch if art.get("content")
            ]

            mongo_client.update_collection_entries(collection, batch_updates)

            pbar.update(len(batch))

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

    articles = mongo_client.get_collection_entries("mediacloud_desempleo")
    get_articles_content(articles, mongo_client, "mediacloud_desempleo")


if __name__ == "__main__":
    main()

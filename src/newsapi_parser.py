from gnews import GNews
from datetime import datetime, timedelta
from time import sleep
from hashlib import sha256
from mongo_wrapper.mongo_wrapper import MongoWrapper
from dotenv import load_dotenv
import os

load_dotenv()

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

def hash_url(url: str) -> str:
    """Generate a unique ID by hashing the URL."""
    return sha256(url.encode('utf-8')).hexdigest()

def fetch_articles(gnews_engine: GNews, keyword: str, start_date: datetime, end_date: datetime) -> list[dict]:
    gnews_engine.start_date = (start_date.year, start_date.month, start_date.day)
    gnews_engine.end_date = (end_date.year, end_date.month, end_date.day)

    try:
        articles = gnews_engine.get_news(keyword)
        for article in articles:
            article["id"] = hash_url(article.get("url", ""))
        return articles
    except Exception as e:
        print(f"Failed to fetch articles: {e}")
        return []

def get_data(gnews_engine: GNews, keyword: str, start_date: datetime, end_date: datetime, country_domain: str = "mx"):
    gnews_engine.country = country_domain
    gnews_engine.language = 'es'
    gnews_engine.max_results = 100

    current_date = start_date
    delta = timedelta(days=10)

    while current_date < end_date:
        next_date = min(current_date + delta, end_date)
        print(f"\nFetching news from {current_date.date()} to {next_date.date()} for keyword: {keyword}")

        articles = fetch_articles(gnews_engine, keyword, current_date, next_date)

        if articles:
            print(f"Got {len(articles)} articles.")
            collection_name = f"gnews_{keyword}"
            mongo_client.save_new_pagination_news(news=articles, collection_name=collection_name)
        else:
            print("No articles found.")

        current_date = next_date
        sleep(3)

def main():
    gnews_engine = GNews()
    get_data(
        gnews_engine,
        keyword="desempleo",
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2022, 12, 1),
        country_domain="mx"
    )

if __name__ == "__main__":
    main()

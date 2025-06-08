from telethon import TelegramClient
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import Any

from tg_scraper import get_posts
from mongo_wrapper.mongo_wrapper import MongoWrapper

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

CHANNEL_USERNAMES = [
    "@elpaismexico",
    "@ElUniversalOnline",
    "@proceso_unofficial",
    "@politicomx",
    "@lajornada_unofficial",
    "@larazondemexico",
    "@sinembargomx",
    "@elpaisamerica",
    "@animalpolitico",
    "@ElEconomista_MTY"
    ]

TARGET_STRINGS = [" "]

START = "01/01/2022"
END = "31/12/2022"

async def save_to_mongo(mongo_client: MongoWrapper, posts: list[Any], channel_username: str):
    mongo_client.save_new_channel_posts(channel=f'{channel_username}_2022', posts=posts)

async def main():
    date_format = "%d/%m/%Y"
    current_date = datetime.strptime(START, date_format)
    end_date = datetime.strptime(END, date_format)

    mongo_client = MongoWrapper(
        db=MONGO_DB,
        user=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        ip=MONGO_IP,
        port=MONGO_PORT
    )

    async with TelegramClient("session", API_ID, API_HASH) as client:
        while current_date < end_date:
            interval_end = current_date + timedelta(days=30)
            if interval_end > end_date:
                interval_end = end_date

            start_str = current_date.strftime(date_format)
            end_str = interval_end.strftime(date_format)

            for index, channel_username in enumerate(CHANNEL_USERNAMES, start=1):
                posts = await get_posts(
                    client=client,
                    channel=channel_username,
                    start=start_str,
                    end=end_str,
                    target_strings=TARGET_STRINGS
                )

                await save_to_mongo(mongo_client, posts, channel_username)
                print(f'{index}/{len(CHANNEL_USERNAMES)} channel {channel_username}: {len(posts)} posts {start_str} to {end_str}')

            current_date = interval_end

if __name__ == "__main__":
    asyncio.run(main())

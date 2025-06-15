from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from typing import Any

from tg_scraper import get_posts
from mongo_wrapper.mongo_wrapper import MongoWrapper

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION")

MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

TARGET_STRINGS = [" "]

async def save_to_mongo(mongo_client: MongoWrapper, posts: list[Any], channel_username: str, start_year: int, end_year: int):
    mongo_client.save_new_channel_posts(channel=f'{channel_username}_{start_year}_{end_year}', posts=posts)

async def download_posts(channels: list[str], start_year: int, end_year: int):
    date_format = "%d/%m/%Y"
    current_date = datetime.strptime(f'01/01/{start_year}', date_format)
    end_date = datetime.strptime(f'31/12/{end_year}', date_format)

    mongo_client = MongoWrapper(
        db=MONGO_DB,
        user=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        ip=MONGO_IP,
        port=MONGO_PORT
    )

    async with TelegramClient(StringSession(TELEGRAM_SESSION), API_ID, API_HASH) as client:
        while current_date < end_date:
            interval_end = current_date + timedelta(days=30)
            print(client.session.save())
            if interval_end > end_date:
                interval_end = end_date

            start_str = current_date.strftime(date_format)
            end_str = interval_end.strftime(date_format)

            for index, channel_username in enumerate(channels, start=1):
                posts = await get_posts(
                    client=client,
                    channel=channel_username,
                    start=start_str,
                    end=end_str,
                    target_strings=TARGET_STRINGS
                )

                await save_to_mongo(mongo_client, posts, channel_username, start_year, end_year)
                print(f'{index}/{len(channels)} channel {channel_username}: {len(posts)} posts {start_str} to {end_str}')

            current_date = interval_end

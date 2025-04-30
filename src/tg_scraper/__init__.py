from telethon import TelegramClient
from datetime import datetime
import pytz
from telegram.post import Post
from telegram.comment import Comment

def transform_to_datetime(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except Exception as e:
        raise ValueError(f'Can not transform {date_str} to datetime. Required format: 07/03/2025')

async def get_posts(
    client: TelegramClient,
    channel: str,
    start: str,
    end: str,
    target_strings: list[str] = []
) -> list[Post]:

    start_dt = pytz.UTC.localize(transform_to_datetime(start))
    end_dt = pytz.UTC.localize(transform_to_datetime(end))

    try:
        posts = []
        async for message in client.iter_messages(
            channel,
            offset_date=end_dt,
            reverse=False
        ):
            if message.date < start_dt:
                break

            if message.date > end_dt:
                continue

            if target_strings and not any(
                word.lower() in (message.text or "").lower()
                for word in target_strings
            ):
                continue

            posts.append(
                Post(
                    id=message.id,
                    text=message.message or "",
                    author=message.sender_id,
                    posting_ts=message.date.timestamp(),
                    comments=[]
                )
            )

        return posts

    except Exception as e:
        print(f'Error gathering posts: {e}')
        return []

async def get_comments(session: TelegramClient, channel: str, post: Post):
    async with session as client:
        try:
            fetched_post = await client.get_messages(channel, ids=post.id)
            if not fetched_post:
                print(f'No post {post.id}')
                return []

            comments = await client.get_messages(
                fetched_post.sender_id,
                reply_to=fetched_post.id,
                limit=1000
            )

            return [
                Comment(
                    comment_id=comment.id,
                    text=comment.message or "",
                    author=comment.sender_id,
                    posting_ts=comment.date.timestamp(),
                    post=post
                )
                for comment in comments
            ]

        except Exception as e:
            print(f"Error: {e}")
            return []

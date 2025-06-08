from telethon import TelegramClient
from datetime import datetime
import pytz
from telegram.post import Post
from telegram.comment import Comment

def transform_to_datetime(date_str: str) -> datetime:
    """
    Convert string in format 'dd/mm/YYYY' to datetime object.
    Example: "07/03/2025" → datetime(2025, 3, 7)
    """
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
    """
    Downloads Telegram posts from a channel within a date range,
    with optional filtering by keyword presence in post text.

    Params:
        - client: initialized Telethon client
        - channel: full @channel name or ID
        - start, end: string dates in format 'dd/mm/YYYY'
        - target_strings: optional list of words to filter posts
    """

    # Convert input date strings into UTC datetime objects
    start_dt = pytz.UTC.localize(transform_to_datetime(start))
    end_dt = pytz.UTC.localize(transform_to_datetime(end))

    try:
        posts = []

        async for message in client.iter_messages(
            channel,
            offset_date=end_dt,  # fetch from this date backward
            reverse=False        # from newest to oldest
        ):
            # Ignore messages outside of time window
            if message.date < start_dt:
                break
            if message.date > end_dt:
                continue

            # If filtering by target words — skip if none found
            if target_strings and not any(
                word.lower() in (message.text or "").lower()
                for word in target_strings
            ):
                continue

            # Save as Post object
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
    """
    For a given Post, fetch replies (comments) using its ID.

    Returns a list of Comment objects.
    """
    async with session as client:
        try:
            # Get original post to find comment thread
            fetched_post = await client.get_messages(channel, ids=post.id)
            if not fetched_post:
                print(f'No post {post.id}')
                return []

            # Grab all replies (limit = 1000)
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


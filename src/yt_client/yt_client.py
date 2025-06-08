from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from typing import Any, List
from mongo_wrapper.mongo_wrapper import MongoWrapper
from logger.logger import Logger

load_dotenv()

MONGO_DB = os.getenv("MONGO_DB")
MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_USER = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

class YouTubeClient:
    def __init__(self, api_key: str):
        # Build YouTube API client
        self.client = build("youtube", "v3", developerKey=api_key)

        # Init Mongo connection
        self.mongo_client = MongoWrapper(
            db=MONGO_DB,
            ip=MONGO_IP,
            user=MONGO_USER,
            password=MONGO_PASSWORD,
            port=MONGO_PORT
        )

        # Init internal logger
        self.logger = Logger(logger_type="yt_client", stream_handler=True)

    def _get_channel_id_by_handle(self, handle: str) -> str:
        """
        Get the channel ID by handle
        
        :param handle: channel handle
        :return: channel ID
        """
        try:
            request = self.client.channels().list(
                part="snippet",
                forHandle=handle
            )

            response = request.execute()
            if len(response["items"]) == 0:
                self.logger.log(
                    f"Channel with handle {handle} not found",
                    level="error"
                )
                return None

            channel_id = response["items"][0]["id"]

            return channel_id
        except Exception as e:
            self.logger.log(
                f"Error getting channel id by handle {handle}: {e}",
                level="error"
            )

            return None
        
    def _get_videos_from_mongo(self, handle: str) -> List[dict]:
        """
        Get videos from MongoDB by channel handle
        
        :param handle: channel handle
        :return: list of videos
        """
        return self.mongo_client.get_videos_by_channel_handle(handle=handle)

    def get_videos_by_handle(self, handle: str, limit: int = 100) -> list[dict]:
        """
        Get videos by channel handle
        
        :param handle: channel handle
        :param limit: maximum number of videos to retrieve
        :return: list of videos
        """
        videos_from_mongo = self._get_videos_from_mongo(handle=handle)
        if len(videos_from_mongo) > 0:
            self.logger.log(
                message=f'Got {len(videos_from_mongo)} videos for {handle} from mongo',
                level="info"
            )
            return videos_from_mongo

        videos = []
        next_page_token = None

        channel_id = self._get_channel_id_by_handle(handle)
        if channel_id is None:
            self.logger.log(
                f"Channel with handle {handle} not found",
                level="error"
            )
            return []

        try:
            while len(videos) < limit:
                request = self.client.search().list(
                    part="snippet",
                    channelId=channel_id,
                    type="video",
                    maxResults=100,
                    pageToken=next_page_token 
                )
                response = request.execute()
                videos.extend(response.get("items", []))
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

                self.logger.log(
                    message=f'Got {len(videos)} videos for {handle}',
                    level="info"
                )

            self.logger.log(
                message=f'Got {len(videos)} videos for {handle}',
                level="info"
            )

            self.mongo_client.save_new_handle_videos(videos=videos, handle=handle)

            return videos
        
        except Exception as e:
            self.logger.log(
                message=f'Can not get videos for {handle}: {e}',
                level="error"
            )
            return []
        
    def _get_keyword_videos_from_mongo(self, keyword: str) -> List[dict]:
        return self.mongo_client.get_videos_by_keyword(keyword=keyword)

    def get_videos_by_keyword(self, keyword: str, published_before: str = None, published_after: str = None, limit: int = 250) -> List[str]:
        """
        Get videos by keyword
        
        :param keyword: keyword
        :param published_before: optional parameter to filter videos published before a specific date
        :param published_after: optional parameter to filter videos published after a specific date
        :param limit: maximum number of videos to retrieve
        :return: list of videos id
        """
        keyword_videos_from_mongo = self._get_keyword_videos_from_mongo(keyword=keyword)
        if len(keyword_videos_from_mongo) > 0:
            self.logger.log(
                message=f'Got {len(keyword_videos_from_mongo)} videos for {keyword} from mongo',
                level="info"
            )

            return keyword_videos_from_mongo

        videos = []
        next_page_token = None

        try: 
            while len(videos) < limit:
                request = self.client.search().list(
                    part="snippet",
                    q=keyword,
                    publishedBefore=published_before,
                    publishedAfter=published_after,
                    safeSearch="none",
                    type="video",
                    maxResults=100,
                    pageToken=next_page_token
                )
                response = request.execute()
                videos.extend(response.get("items", []))

                self.logger.log(
                    message=f'Got {len(videos)} videos for {keyword}',
                    level="info"
                )

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            self.mongo_client.save_new_keyword_videos(videos=videos, keyword=f'{keyword}_2020')

            return videos
        except Exception as e:
            self.logger.log(
                f"Error getting videos by keyword {keyword}: {e}",
                level="error"
            )
            return []
        
    def _get_comments_from_mongo(self, video_id: str) -> List[dict]:
        """
        Get comments from MongoDB by video ID
        
        :param video_id: video ID
        :return: list of comments
        """
        return self.mongo_client.get_comments_by_video_id(video_id=video_id)

    def get_comments_by_video_id(self, video_id: str, limit: int = 1000) -> List[dict]:
        """
        Get comments by video ID
        
        :param video_id: video ID
        :param limit: maximum number of comments to retrieve
        :return: list of comments
        """
        # In case we have comments in the db, we will use them
        comments_from_db = self._get_comments_from_mongo(video_id)
        if len(comments_from_db) > 0:
            self.logger.log(
                message=f'Got {len(comments_from_db)} comments for video {video_id} from mongo',
                level="info"
            )
            return comments_from_db

        # Otherwise, we will get them from the youtube api
        result = []
        page_result = limit
        next_page_token = None
        try:
            # Get the first page of comments
            while page_result == limit:
                request = self.client.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=limit,
                    textFormat="plainText",
                    pageToken=next_page_token
                )
                response = request.execute()
                current_page_comments = response["items"]

                result += current_page_comments 

                self.logger.log(
                    message=f'Got {len(result)} comments for video {video_id}',
                    level="info"
                )

                page_result = response["pageInfo"]["totalResults"]
                next_page_token = response.get("nextPageToken", None)
                if next_page_token is None:
                    break

            self.mongo_client.save_new_yt_comments(comments=result)

            return result

        except Exception as e:
            self.logger.log(
                f"Error getting comments by video id {video_id}: {e}",
                level="error"
            )
            return []

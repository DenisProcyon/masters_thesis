import pymongo
import pymongo.errors

from time import sleep

from text_objects.telegram import Post
from text_objects.youtube import Comment
from logger.logger import Logger

def serialize_posts(posts: list[Post]) -> list[dict]:
    result = []
    for post in posts:
        post_comments = [
            {
                "id": comment.id,
                "text": comment.text,
                "author": comment.author,
                "posting_ts": comment.posting_ts,
                "post_id": comment.post.id 
            }
            for comment in post.comments
        ]

        result.append(
            {
                "id": post.id,
                "text": post.text,
                "author": post.author,
                "posting_ts": post.posting_ts,
                "comments": post_comments
            }
        )

    return result

class MongoWrapper:
    def __init__(self, db: str, user: str, password: str, ip: str = "localhost", port: int = 27017):
        self.mongo_client = pymongo.MongoClient(
            f'mongodb://{user}:{password}@{ip}:{port}/',
            serverSelectionTimeoutMS=1000
        )

        self.logger = Logger(logger_type="Mongo", stream_handler=True)

        # Check if reachable and there is db
        if self.__connected() and db in self.mongo_client.list_database_names():
            self.logger.log(f'Connected to {db} database on {ip}', level="info")
            self.database = self.mongo_client[db]
        else:
            self.logger.log(f'No {db} in database list or not connected', level="error")

    def __connected(self):
        connections = 0
        while connections <= 5:
            try:
                # Check if host reachable
                self.mongo_client.admin.command("ismaster")
                return True
            except Exception as e:
                self.logger.log(f'Can not connect to mongo client host: {e}. Reconnecting.', level="error")
                connections = connections + 1
                sleep(1)

    def remove_duplicates(self, entries: list[dict], custom_key: str = None) -> list[dict]:
        original_length = len(entries)

        if custom_key:
            unique_dict = {d[custom_key.split(".")[0]][custom_key.split(".")[1]]: d for d in entries}
        else:
            unique_dict = {d["id"]: d for d in entries}

        self.logger.log(
            message=f'Removed {original_length - len(unique_dict)} duplicates from entries',
            level="warning"
        )

        return list(unique_dict.values())
    
    def get_all_collections(self):
        return self.database.list_collection_names()
    
    def get_all_db_entries(self) -> list:
        collections = self.get_all_collections()
        
        result = []
        for collection in collections:
            data = self.database[collection].find()
            for i in data:
                result.append(i)

        return result

    def get_collection_entries(self, collection: str):
        try:
            existing_collection = self.database[collection]
            
            result = [i for i in existing_collection.find()]

            return result
        except Exception as e:
            self.logger.log(f'Can not get collection {collection} from db: {e}', level="error")

            return []

    def get_document_by_id(self, collection: str, id: str):
        collection = self.database[collection]

        try:
            result = collection.find_one(
                {
                    "_id": id
                }
            )

            return result
        except Exception as e:
            self.logger.log(f'Can not get document from {collection} with {id} id - {e}', level="error")

    def assign_entry_ids(self, entries: list[dict], name: str = None, custom: bool = True) -> list[dict]:
        """
        :param entries: entries
        :param name: name of the field to be _id
        :param custom: if True, pass the name param to be _id, otherwise will be saved with incremental id

        Since mongo needs _id field, we assign it for each of the entry
        """
        if custom:
            change_key = lambda d, old_key, new_key: {new_key if k == old_key else k: v for k, v in d.items()}
            entries = list(map(lambda d: change_key(d, name, '_id'), entries))
        else:
            entries = [{'_id': i, **d} for i, d in enumerate(entries)]

        return entries
    
    def save_new_handle_videos(self, videos: list[dict], handle: str):
        cleaned_videos = self.remove_duplicates(videos, custom_key="id.videoId")
        videos_to_save = self.assign_entry_ids(cleaned_videos, name="id", custom=True)
        
        if handle not in self.get_all_collections():
            self.logger.log(message=f'Collection for handle {handle} was not found in db. Creating...', level="info")
            self.create_new_channel_collection(handle)

        try:
            self.database[handle].insert_many(videos_to_save)
            self.logger.log(
            message=f'Inserted {len(videos_to_save)} new videos into collection {handle}',
            level="info"
            )
        except Exception as e:
            self.logger.log(
            message=f'Could not insert new videos into collection: {e}',
            level="error"
            )
    
    def save_new_yt_comments(self, comments: list[dict]):
        cleaned_comments = self.remove_duplicates(comments)

        comments_to_save = self.assign_entry_ids(cleaned_comments, name="id", custom=True)

        existing_posts = self.get_collection_entries(collection="yt_comments")
        if not existing_posts:
            existing_posts = []

        existing_ids = {post["_id"] for post in existing_posts}

        new_comments = [c for c in comments_to_save if c["_id"] not in existing_ids]

        if new_comments:
            try:
                self.database["yt_comments"].insert_many(new_comments)
                self.logger.log(
                    message=f'Inserted {len(new_comments)} new comments into collection',
                    level="info"
                )
            except Exception as e:
                self.logger.log(
                    message=f'Could not insert new posts into collection: {e}',
                    level="error"
                )
        else:
            self.logger.log(
                message=f'No new comments to insert',
                level="info"
            )
    
    def get_comments_by_video_id(self, video_id: str) -> list[dict]:
        try:
            collection = self.database["yt_comments"]

            comments = list(collection.find({"snippet.videoId": video_id}))
            
            if not comments:
                self.logger.log(
                    message=f"No comments found for video {video_id}",
                    level="warning"
                )
                
            return comments
        except Exception as e:
            self.logger.log(
                message=f"Can not get comments for video {video_id}: {e}",
                level="error"
            )
            return []
        
    def save_new_keyword_videos(self, videos: list[dict], keyword: str):
        cleaned_videos = self.remove_duplicates(videos, custom_key="id.videoId")
        videos_to_save = self.assign_entry_ids(cleaned_videos, name="id", custom=True)
        
        if keyword not in self.get_all_collections():
            self.logger.log(message=f'Collection for keyword {keyword} was not found in db. Creating...', level="info")
            self.create_new_channel_collection(keyword)

        try:
            self.database[keyword].insert_many(videos_to_save)
            self.logger.log(
            message=f'Inserted {len(videos_to_save)} new videos into collection {keyword}',
            level="info"
            )
        except Exception as e:
            self.logger.log(
            message=f'Could not insert new videos into collection: {e}',
            level="error"
            )
        
    def get_videos_by_keyword(self, keyword: str) -> list[dict]:
        """
        :param keyword: keyword to search for

        Method to get videos by keyword
        """
        try:
            videos = self.get_collection_entries(keyword)

            if not videos:
                self.logger.log(
                    message=f"No videos found for keyword {keyword}",
                    level="warning"
                )
                
            return videos
        except Exception as e:
            self.logger.log(
                message=f"Can not get videos for keyword {keyword}: {e}",
                level="error"
            )
            return []
        
    def get_videos_by_channel_handle(self, handle: str) -> list[dict]:
        """
        :param keyword: keyword to search for

        Method to get videos by keyword
        """
        try:
            videos = self.get_collection_entries(handle)

            if not videos:
                self.logger.log(
                    message=f"No videos found for handle {handle}",
                    level="warning"
                )
                
            return videos
        except Exception as e:
            self.logger.log(
                message=f"Can not get videos for handle {handle}: {e}",
                level="error"
            )
            return []
    
    def create_new_channel_collection(self, channel_name: str) -> None:
        """
        :param channel_name: channel name, collection name

        Creates new collection
        """
        try:
            self.database.create_collection(channel_name)
            self.logger.log(message=f'Collection for {channel_name} was created', level="info")

        except Exception as e:
            self.logger.log(message=f'Could not create new collection for {channel_name}: {e}', level="error")
            raise ConnectionError(f'Can not create new collection for {channel_name}: {e}')
    
    def save_new_channel_posts(self, channel: str, posts: Post) -> None:
        """
        :param channel: name of the channel, collection name
        "param posts: list of Post objects

        Method either saves new data to existing collection in db or creates new collection and saves all the data passed
        """
        channel_name = channel.replace("@", "")
        if channel_name not in self.get_all_collections():
            self.logger.log(message=f'Collection for channel {channel} was not found in db. Creating...', level="info")
            self.create_new_channel_collection(channel_name)

        serialized_posts = serialize_posts(posts=posts)
        posts_to_save = self.assign_entry_ids(serialized_posts, name="id", custom=True)

        existing_posts = self.get_collection_entries(collection=channel_name)
        if not existing_posts:
            existing_posts = []

        existing_ids = {post["_id"] for post in existing_posts}

        new_posts = [p for p in posts_to_save if p["_id"] not in existing_ids]

        if new_posts:
            try:
                self.database[channel_name].insert_many(new_posts)
                self.logger.log(
                    message=f'Inserted {len(new_posts)} new posts into collection {channel_name}',
                    level="info"
                )
            except Exception as e:
                self.logger.log(
                    message=f'Could not insert new posts into {channel_name}: {e}',
                    level="error"
                )
        else:
            self.logger.log(
                message=f'No new posts to insert for {channel_name}',
                level="info"
            )
from typing import Any

class Comment:
    def __init__(self, id: int | str, text: str, author: str, posting_ts: int, video: str):
        self.id = id
        self.text = text
        self.author = author
        self.posting_ts = posting_ts
        self.video = video

    def __str__(self) -> str:
        return self.text
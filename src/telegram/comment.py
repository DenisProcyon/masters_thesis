from typing import Any

class Comment:
    def __init__(self, id: int | str, text: str, author: str, posting_ts: int, post: "Post"):
        self.id = id
        self.text = text
        self.author = author
        self.posting_ts = posting_ts
        self.post = post

    def __str__(self) -> str:
        return self.text
class Post:
    def __init__(self, id: int | str, text: str, author: str, posting_ts: int, comments: list["Comment"] = []) -> None:
        self.id = id
        self.text = text
        self.author = author
        self.posting_ts = posting_ts
        self.comments = comments

    def __str__(self) -> str:
        return self.text
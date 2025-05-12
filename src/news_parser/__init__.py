import hashlib
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Article:
    source: Optional[str] = None
    date: Optional[datetime] = None
    summary: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    id: Optional[str] = field(init=False)

    def __post_init__(self):
        if self.url:
            parsed = urlparse(self.url)
            cleaned_url = urlunparse(parsed._replace(query="", fragment=""))
            self.url = cleaned_url

            self.id = hashlib.md5(self.url.encode('utf-8')).hexdigest()
        else:
            self.id = None

@dataclass
class ContentParserResponse:
    content: List[Article]

@dataclass
class CssSelectors:
    feed: str
    title: str
    summary: Optional[str] = None
    text: Optional[str] = None
    date: Optional[str] = None
    tags: Optional[str] = None
    image: Optional[str] = None
import asyncio
from typing import Optional, List

import aiohttp
from bs4 import BeautifulSoup

from news_parser import Article, ContentParserResponse, CssSelectors
from logger.logger import Logger


class HTMLContentParser:
    def __init__(self, name: str, base_url: str, selectors: CssSelectors):
        self.name = name
        self.base_url = base_url
        self.selectors = selectors

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Host": self.base_url.split("//")[-1].split("/")[0],
        }

        self.logger = Logger(logger_type=f'{self.name}_html_parser', stream_handler=True)

        self.bs_content = None 

    async def __configure_async(self) -> bool:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.base_url) as response:
                    if response.status != 200:
                        self.logger.log(
                            message=f'Can not connect to {self.base_url}: {response.status}',
                            level="error"
                        )
                        return False
                    content = await response.read()
                    self.bs_content = BeautifulSoup(content, "lxml")

                    self.logger.log(
                        message=f'Connected to {self.base_url}',
                        level="info"
                    )

                    return True
        except Exception as e:
            self.logger.log(
                message=f'Can not load BS: {e}',
                level="error"
            )
            return False

    def _get_article_links(self) -> List[str]:
        article_links = []
        articles = self.bs_content.select(self.selectors.feed)
        for article in articles:
            href = article.attrs.get("href")
            if href:
                if self.base_url not in href:
                    href = f'{self.base_url}{href}'

                article_links.append(href)
        self.logger.log(
            message=f'Got {len(article_links)} article links',
            level="info"
        )
        return article_links

    def _process_selector(self, selector: str, article_link: str, page_content: BeautifulSoup) -> Optional[str]:
        if not selector:
            return None
        try:
            element = page_content.select_one(selector)
            return element.get_text().strip() if element else None
        except Exception as e:
            self.logger.log(
                message=f'Can not get text for selector: {selector} for {article_link}: {e}',
                level="error"
            )
            return None

    async def _parse_article(self, article_link: str) -> Article:
        article = Article()
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(article_link) as response:
                    if response.status != 200:
                        self.logger.log(
                            message=f'Article page {article_link} returned status {response.status}',
                            level="error"
                        )
                        return article
                    content = await response.read()
                    page_content = BeautifulSoup(content, "lxml")
        except Exception as e:
            self.logger.log(
                message=f'Error fetching article {article_link}: {e}',
                level="error"
            )
            return article

        article_title = self._process_selector(self.selectors.title, article_link, page_content)
        article_summary = self._process_selector(self.selectors.summary, article_link, page_content)
        article_text = self._process_selector(self.selectors.text, article_link, page_content)
        
        try:
            date_element = page_content.select_one(self.selectors.date)
            article_datetime = date_element.attrs.get("datetime") if date_element and date_element.attrs.get("datetime") else None
        except Exception as e:
            self.logger.log(
                message=f'Error fetching date for {article_link}: {e}',
                level="error"
            )
            article_datetime = None

        article = Article(
            source=self.base_url,
            date=article_datetime,
            summary=article_summary,
            title=article_title,
            content=article_text,
            url=article_link
        )

        return article

    async def _get_articles(self, article_links: List[str]) -> List[Article]:
        tasks = [self._parse_article(link) for link in article_links]
        articles = await asyncio.gather(*tasks)
        self.logger.log(
            message=f'Got {len(articles)} articles',
            level="info"
        )
        return articles

    async def collect(self) -> ContentParserResponse:
        if not await self.__configure_async():
            raise ConnectionError("Configuration error")
        
        article_links = self._get_article_links()
        articles = await self._get_articles(article_links)

        return ContentParserResponse(content=articles)
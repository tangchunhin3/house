import re
import time
import random
from abc import ABC, abstractmethod
from typing import Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

from app.config import settings

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}


def get_soup(url: str) -> BeautifulSoup:
    time.sleep(settings.request_delay_seconds * random.uniform(0.5, 1.5))
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


class PlaywrightSession:
    def __init__(self, channel=None):
        self._pw_cm = None
        self._browser: Optional[Browser] = None
        self._channel = channel

    async def __aenter__(self):
        self._pw_cm = async_playwright()
        pw = await self._pw_cm.__aenter__()
        launch_kwargs = {"headless": settings.playwright_headless}
        if self._channel:
            launch_kwargs["channel"] = self._channel
        self._browser = await pw.chromium.launch(**launch_kwargs)
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._pw_cm:
            await self._pw_cm.__aexit__(*args)

    async def new_page(self) -> Page:
        ctx = await self._browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1920, "height": 1080},
            locale="zh-HK",
        )
        return await ctx.new_page()

    @staticmethod
    async def delay():
        import asyncio
        await asyncio.sleep(settings.request_delay_seconds * random.uniform(0.5, 1.5))


class RequestScraper(ABC):
    SOURCE_NAME: str = ""

    def build_property(self, **kwargs) -> dict:
        return {
            "title": kwargs.get("title", ""),
            "price": kwargs.get("price", 0),
            "area_sqft": kwargs.get("area_sqft"),
            "bedrooms": kwargs.get("bedrooms"),
            "floor": kwargs.get("floor"),
            "estate_name": kwargs.get("estate_name"),
            "address": kwargs.get("address"),
            "district": "屯門",
            "source": self.SOURCE_NAME,
            "source_url": kwargs.get("source_url", ""),
            "image_url": kwargs.get("image_url"),
            "description": kwargs.get("description"),
            "is_transaction": kwargs.get("is_transaction", False),
        }

    @abstractmethod
    def scrape(self) -> list[dict]:
        ...


class PlaywrightScraper(ABC):
    SOURCE_NAME: str = ""

    def __init__(self, session: PlaywrightSession, keyword: str = ""):
        self.session = session
        self.keyword = keyword

    def build_property(self, **kwargs) -> dict:
        return {
            "title": kwargs.get("title", ""),
            "price": kwargs.get("price", 0),
            "area_sqft": kwargs.get("area_sqft"),
            "bedrooms": kwargs.get("bedrooms"),
            "floor": kwargs.get("floor"),
            "estate_name": kwargs.get("estate_name"),
            "address": kwargs.get("address"),
            "district": "屯門",
            "source": self.SOURCE_NAME,
            "source_url": kwargs.get("source_url", ""),
            "image_url": kwargs.get("image_url"),
            "description": kwargs.get("description"),
            "is_transaction": kwargs.get("is_transaction", False),
        }

    @abstractmethod
    async def scrape(self) -> list[dict]:
        ...


def parse_price(text: str) -> int:
    m = re.search(r"\$?\s*([\d,]+\.?\d*)\s*萬", text)
    if m:
        return int(float(m.group(1).replace(",", "")) * 10000)
    return 0


def parse_area(text: str) -> Optional[float]:
    m = re.search(r"(\d+[\d,]*)\s*呎", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_bedrooms(text: str) -> Optional[int]:
    m = re.search(r"(\d)\s*房", text)
    if m:
        return int(m.group(1))
    return None

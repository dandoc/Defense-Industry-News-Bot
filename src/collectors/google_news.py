"""
Google News RSS 기반 국방 및 방산 뉴스 수집기
Google News RSS는 차단 없이 실시간으로 국내외 언론사의 방산 뉴스를 빠르게 수집할 수 있습니다.
"""

import urllib.parse
import asyncio
from typing import List, Optional
from datetime import datetime, timezone
import calendar
from zoneinfo import ZoneInfo
import aiohttp
import feedparser
from bs4 import BeautifulSoup

from src.collectors.base import BaseNewsCollector, NewsItem
from src.config import Config


class GoogleNewsCollector(BaseNewsCollector):
    RSS_BASE_URL = "https://news.google.com/rss/search"

    def __init__(self):
        super().__init__(name="Google News (Defense/Arms)")

    def _build_rss_url(self, query: str) -> str:
        params = {
            "q": query,
            "hl": "ko",
            "gl": "KR",
            "ceid": "KR:ko"
        }
        return f"{self.RSS_BASE_URL}?{urllib.parse.urlencode(params)}"

    def _clean_html(self, raw_html: str) -> str:
        """HTML 태그 제거 및 텍스트 정제"""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    def _parse_entry(self, entry) -> Optional[NewsItem]:
        try:
            title_full = entry.get("title", "")
            # Google News RSS 제목은 통상 "기사 제목 - 언론사" 형태
            if " - " in title_full:
                title, source = title_full.rsplit(" - ", 1)
                title = title.strip()
                source = source.strip()
            else:
                title = title_full.strip()
                source = entry.get("source", {}).get("title", "Google 뉴스")

            link = entry.get("link", "")
            if not link or not title:
                return None

            # 요약 및 본문 정리
            summary_raw = entry.get("summary", "")
            summary = self._clean_html(summary_raw)

            # 발행 시각 파싱
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                dt = datetime.fromtimestamp(calendar.timegm(published_parsed), tz=timezone.utc).astimezone(ZoneInfo("Asia/Seoul"))
                published_at = dt.strftime("%Y-%m-%d %H:%M")
            else:
                published_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            return NewsItem(
                title=title,
                url=link,
                source=source,
                summary=summary,
                published_at=published_at
            )
        except Exception as e:
            print(f"[GoogleNewsCollector] Parse error: {e}")
            return None

    async def fetch_news(self, query: Optional[str] = None, limit: int = 10) -> List[NewsItem]:
        queries_to_fetch = [query] if query else Config.DEFAULT_QUERIES
        items: List[NewsItem] = []
        seen_urls = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as session:
            for q in queries_to_fetch:
                url = self._build_rss_url(q)
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            feed = feedparser.parse(content)
                            for entry in feed.entries:
                                news_item = self._parse_entry(entry)
                                if news_item and news_item.url not in seen_urls:
                                    seen_urls.add(news_item.url)
                                    items.append(news_item)
                                    if len(items) >= limit:
                                        break
                except Exception as e:
                    print(f"[GoogleNewsCollector] Request failed for query '{q}': {e}")

                if len(items) >= limit:
                    break

        return items[:limit]

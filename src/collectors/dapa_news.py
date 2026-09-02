"""
방위사업청(DAPA) 및 국방부(MND) 공식 보도자료 및 소식 수집기
공식 정부 출처의 신뢰도 높은 무기체계 개발, 계약 체결, 정책 발표 소식을 수집합니다.
"""

import urllib.parse
from typing import List, Optional
from datetime import datetime, timezone
import calendar
from zoneinfo import ZoneInfo
import aiohttp
import feedparser
from bs4 import BeautifulSoup

from src.collectors.base import BaseNewsCollector, NewsItem


class DapaNewsCollector(BaseNewsCollector):
    def __init__(self):
        super().__init__(name="DAPA/MND Official News")

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    async def fetch_news(self, query: Optional[str] = None, limit: int = 5) -> List[NewsItem]:
        """방위사업청 및 국방부 공식 보도자료/주요 브리핑 수집"""
        base_query = '방위사업청 보도자료 OR 국방부 보도자료 OR "방위사업청"'
        if query:
            base_query = f'({base_query}) {query}'

        params = {
            "q": base_query,
            "hl": "ko",
            "gl": "KR",
            "ceid": "KR:ko"
        }
        url = f"https://news.google.com/rss/search?{urllib.parse.urlencode(params)}"

        items: List[NewsItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        feed = feedparser.parse(content)
                        for entry in feed.entries:
                            title_full = entry.get("title", "")
                            if " - " in title_full:
                                title, source = title_full.rsplit(" - ", 1)
                                title = title.strip()
                                source = source.strip()
                            else:
                                title = title_full.strip()
                                source = "방위사업청/국방부"

                            link = entry.get("link", "")
                            if not link or not title:
                                continue

                            summary = self._clean_html(entry.get("summary", ""))

                            published_parsed = entry.get("published_parsed")
                            if published_parsed:
                                dt = datetime.fromtimestamp(calendar.timegm(published_parsed), tz=timezone.utc).astimezone(ZoneInfo("Asia/Seoul"))
                                published_at = dt.strftime("%Y-%m-%d %H:%M")
                            else:
                                published_at = datetime.now().strftime("%Y-%m-%d %H:%M")

                            item = NewsItem(
                                title=title,
                                url=link,
                                source=f"📢 {source}",
                                summary=summary,
                                published_at=published_at,
                                category="국방정책/공식",
                                badge="📢 [공식/보도자료]"
                            )
                            items.append(item)
                            if len(items) >= limit:
                                break
        except Exception as e:
            print(f"[DapaNewsCollector] Fetch error: {e}")

        return items

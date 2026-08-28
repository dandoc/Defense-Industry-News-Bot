"""
네이버 뉴스 수집기
- 네이버 오픈 API (Client ID / Secret 등록 시 고속 JSON 수집)
- API 키가 없는 경우에도 안전하게 스킵하거나 대체 처리
"""

import html
import urllib.parse
from typing import List, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

from src.collectors.base import BaseNewsCollector, NewsItem
from src.config import Config


class NaverNewsCollector(BaseNewsCollector):
    API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self):
        super().__init__(name="Naver News")

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        # 네이버 API는 <b>태그와 &quot; 등 HTML 엔티티를 반환함
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(separator=" ", strip=True)
        return html.unescape(cleaned)

    async def fetch_news(self, query: Optional[str] = None, limit: int = 5) -> List[NewsItem]:
        client_id = Config.NAVER_CLIENT_ID
        client_secret = Config.NAVER_CLIENT_SECRET

        if not client_id or not client_secret:
            # API 키가 설정되지 않은 경우 조용히 빈 리스트 반환
            return []

        search_query = query if query else "방산 OR 국방 OR 방위산업"
        params = {
            "query": search_query,
            "display": min(limit, 20),
            "sort": "sim"  # 유사도순 (sim) 또는 최신순 (date)
        }
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "User-Agent": "DefenseNewsBot/1.0"
        }

        items: List[NewsItem] = []
        try:
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(self.API_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("items", []):
                            title = self._clean_text(item.get("title", ""))
                            link = item.get("originallink") or item.get("link", "")
                            description = self._clean_text(item.get("description", ""))
                            pub_date_raw = item.get("pubDate", "")

                            # pubDate 파싱 (예: Fri, 28 Aug 2026 14:00:00 +0900)
                            try:
                                dt = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %z")
                                published_at = dt.strftime("%Y-%m-%d %H:%M")
                            except Exception:
                                published_at = datetime.now().strftime("%Y-%m-%d %H:%M")

                            items.append(NewsItem(
                                title=title,
                                url=link,
                                source="네이버 뉴스",
                                summary=description,
                                published_at=published_at
                            ))
                            if len(items) >= limit:
                                break
                    else:
                        print(f"[NaverNewsCollector] API responded with status {resp.status}")
        except Exception as e:
            print(f"[NaverNewsCollector] Request failed: {e}")

        return items

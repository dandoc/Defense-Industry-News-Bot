"""
네이버 뉴스 수집기
- 네이버 클라우드 플랫폼(NCP) NAVER API HUB 및 기존 네이버 개발자 센터 API 동시 지원
- API 키가 설정되지 않은 경우 안전하게 스킵 처리
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
    # 1. 네이버 클라우드 플랫폼 (NCP) NAVER API HUB 엔드포인트
    NCP_API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
    # 2. 기존 개발자 센터 엔드포인트 (레거시)
    LEGACY_API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self):
        super().__init__(name="Naver News")

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(separator=" ", strip=True)
        return html.unescape(cleaned)

    async def fetch_news(self, query: Optional[str] = None, limit: int = 5) -> List[NewsItem]:
        client_id = Config.NAVER_CLIENT_ID
        client_secret = Config.NAVER_CLIENT_SECRET

        if not client_id or not client_secret:
            return []

        search_query = query if query else "방산 OR 국방 OR 방위산업"
        params = {
            "query": search_query,
            "display": min(limit, 20),
            "sort": "sim"
        }

        # 먼저 NCP NAVER API HUB 방식으로 시도, 실패 시 레거시 방식으로 폴백
        auth_configs = [
            {
                "url": self.NCP_API_URL,
                "headers": {
                    "X-NCP-APIGW-API-KEY-ID": client_id,
                    "X-NCP-APIGW-API-KEY": client_secret,
                    "User-Agent": "DefenseNewsBot/1.0"
                }
            },
            {
                "url": self.LEGACY_API_URL,
                "headers": {
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                    "User-Agent": "DefenseNewsBot/1.0"
                }
            }
        ]

        items: List[NewsItem] = []

        for config in auth_configs:
            try:
                async with aiohttp.ClientSession(headers=config["headers"], timeout=aiohttp.ClientTimeout(total=8)) as session:
                    async with session.get(config["url"], params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for item in data.get("items", []):
                                title = self._clean_text(item.get("title", ""))
                                link = item.get("originallink") or item.get("link", "")
                                description = self._clean_text(item.get("description", ""))
                                pub_date_raw = item.get("pubDate", "")

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
                            if items:
                                return items
                        elif resp.status in (401, 403):
                            # 다음 인증 방식 시도
                            continue
            except Exception as e:
                # 다음 인증 시도
                continue

        return items

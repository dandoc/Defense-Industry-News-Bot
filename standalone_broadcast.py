"""
단독 실행 및 웹훅/카카오톡 브로드캐스터 (standalone_broadcast.py)
- 디스코드 봇 구동 없이 터미널에서 즉시 최신 국방/방산 뉴스를 확인하거나,
- DISCORD_WEBHOOK_URL 또는 카카오톡(나와의 채팅)으로 즉시 전송을 테스트합니다.
"""

import sys
import asyncio
import json
import urllib.request
from typing import List

# 콘솔 인코딩 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.config import Config
from src.services.news_service import news_service
from src.services.kakao_sender import kakao_sender
from src.collectors.base import NewsItem


def send_to_discord_webhook(webhook_url: str, item: NewsItem) -> bool:
    """디스코드 웹훅으로 뉴스 카드 전송"""
    from src.services.embed_builder import CATEGORY_COLORS

    branches_str = " ".join(f"`{b}`" for b in item.branches) if item.branches else "`전군/공통`"
    domains_str = " ".join(f"`{d}`" for d in item.domains) if item.domains else "`종합방산`"
    companies_str = " ".join(f"`{c}`" for c in item.companies) if item.companies else "`정부/기타`"

    payload = {
        "embeds": [
            {
                "title": f"{item.badge} {item.title}",
                "url": item.url,
                "description": item.summary if item.summary else "기사 원문 링크를 확인하세요.",
                "color": CATEGORY_COLORS.get(item.category, 0x5865F2),
                "fields": [
                    {"name": "🪖 군종", "value": branches_str, "inline": True},
                    {"name": "🔬 산업분야", "value": domains_str, "inline": True},
                    {"name": "🏢 방산기업", "value": companies_str, "inline": True},
                    {"name": "📰 언론사", "value": item.source, "inline": True},
                    {"name": "⏰ 발행시각", "value": item.published_at, "inline": True}
                ],
                "footer": {
                    "text": "국방·방산 뉴스 알리미 | DefenseNewsBot"
                }
            }
        ]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DefenseNewsBot-Webhook"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Discord Error] Failed: {e}")
        return False


async def run_standalone():
    print("=" * 60)
    print("🛡️ 국방·방산 뉴스 수집 및 다차원 태그 테스트")
    print("=" * 60)

    # 1. 최신 뉴스 수집
    items = await news_service.fetch_all_news(limit=6)
    print(f"\n총 {len(items)}개의 최신 뉴스를 수집했습니다:\n")

    for i, item in enumerate(items, 1):
        print(f"[{i}] {item.badge} {item.title}")
        print(f"    - 출처/발행: {item.source} ({item.published_at})")
        print(f"    - 🪖 군종 태그: {item.branches if item.branches else ['전군/공통']}")
        print(f"    - 🔬 산업분야 : {item.domains if item.domains else ['종합방산']}")
        print(f"    - 🏢 방산기업 : {item.companies if item.companies else ['정부/기타']}")
        print(f"    - URL: {item.url}")
        print("-" * 60)

    # 2. 디스코드 웹훅 전송
    if Config.DISCORD_WEBHOOK_URL:
        print(f"\n[Discord] 웹훅 전송 테스트 중...")
        unseen = await news_service.get_unseen_news(limit=2)
        for item in unseen:
            success = send_to_discord_webhook(Config.DISCORD_WEBHOOK_URL, item)
            print(f" - [{ '성공' if success else '실패' }] {item.title}")

    # 3. 카카오톡 나에게 보내기 전송
    if Config.KAKAO_REST_API_KEY and Config.KAKAO_REFRESH_TOKEN:
        print(f"\n[KakaoTalk] 내 카카오톡으로 전송 테스트 중...")
        if items:
            k_success = kakao_sender.send_news_item(items[0])
            print(f" - [{ '카카오톡 전송 성공' if k_success else '실패' }] {items[0].title}")


if __name__ == "__main__":
    asyncio.run(run_standalone())

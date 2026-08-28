"""
단독 실행 및 웹훅 브로드캐스터 (standalone_broadcast.py)
- 디스코드 봇 구동 없이 터미널에서 즉시 최신 국방/방산 뉴스를 확인하거나,
- DISCORD_WEBHOOK_URL이 설정된 경우 디스코드 채널로 웹훅 전송을 수행합니다.
- Windows 작업 스케줄러나 cron 등으로 주기 실행할 때도 유용합니다.
"""

import sys
import asyncio
import json
import urllib.request
from typing import List

# Windows 콘솔 인코딩 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.config import Config
from src.services.news_service import news_service
from src.collectors.base import NewsItem


def send_to_webhook(webhook_url: str, item: NewsItem) -> bool:
    """디스코드 웹훅으로 뉴스 카드 전송"""
    # 카테고리 컬러 매핑
    color_map = {
        "유도무기/방공": 0xE74C3C,
        "항공/우주/드론": 0x3498DB,
        "기갑/화력/기동": 0x27AE60,
        "함정/해양/잠수함": 0x1F4E79,
        "지휘통신/레이더/센서": 0x9B59B6,
        "해외수출/계약": 0xF1C40F,
        "국방정책/전력화": 0x34495E,
        "일반국방": 0x5865F2
    }

    branches_str = " ".join(f"`{b}`" for b in item.branches) if item.branches else "`전군/공통`"
    domains_str = " ".join(f"`{d}`" for d in item.domains) if item.domains else "`종합방산`"
    companies_str = " ".join(f"`{c}`" for c in item.companies) if item.companies else "`정부/기타`"

    payload = {
        "embeds": [
            {
                "title": f"{item.badge} {item.title}",
                "url": item.url,
                "description": item.summary if item.summary else "기사 원문 링크를 확인하세요.",
                "color": color_map.get(item.category, 0x5865F2),
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
        with urllib.request.urlopen(req) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Webhook Error] Failed to send webhook: {e}")
        return False


async def run_standalone():
    print("=" * 60)
    print("🛡️ 국방·방산 뉴스 수집 및 다차원 태그 테스트 실행")
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

    # 2. 웹훅 전송 (URL이 있는 경우)
    if Config.DISCORD_WEBHOOK_URL:
        print(f"\n[Webhook] {Config.DISCORD_WEBHOOK_URL} 로 전송을 시도합니다...")
        unseen = await news_service.get_unseen_news(limit=3)
        for item in unseen:
            success = send_to_webhook(Config.DISCORD_WEBHOOK_URL, item)
            print(f" - [{ '성공' if success else '실패' }] {item.title}")
    else:
        print("\n💡 알림: .env에 DISCORD_WEBHOOK_URL을 지정하면 웹훅으로도 즉시 전송할 수 있습니다.")


if __name__ == "__main__":
    asyncio.run(run_standalone())

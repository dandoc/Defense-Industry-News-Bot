"""
GitHub Actions 및 스케줄러 전용 웹훅 & 카카오톡 뉴스 브로드캐스터 (webhook_cron.py)
- 디스코드 웹훅(DISCORD_WEBHOOK_URL) 및 카카오톡 나에게 보내기(KAKAO_REFRESH_TOKEN) 지원
- SQLite DB(data/news.db)에 전송 이력을 기록하여 중복 전송 방지
"""

import os
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
from src.services.embed_builder import CATEGORY_COLORS
from src.services.kakao_sender import kakao_sender
from src.collectors.base import NewsItem


def send_article_to_discord(webhook_url: str, item: NewsItem) -> bool:
    """단일 뉴스 카드를 디스코드 웹훅으로 전송"""
    branches_str = " ".join(f"`{b}`" for b in item.branches) if item.branches else "`전군/공통`"
    domains_str = " ".join(f"`{d}`" for d in item.domains) if item.domains else "`종합방산`"
    companies_str = " ".join(f"`{c}`" for c in item.companies) if item.companies else "`정부/기타`"

    color = CATEGORY_COLORS.get(item.category, 0x5865F2)

    payload = {
        "embeds": [
            {
                "title": f"{item.badge} {item.title}",
                "url": item.url,
                "description": item.summary if item.summary else "기사 원문 링크를 클릭하여 상세 내용을 확인하세요.",
                "color": color,
                "fields": [
                    {"name": "🪖 군종", "value": branches_str, "inline": True},
                    {"name": "🔬 산업분야", "value": domains_str, "inline": True},
                    {"name": "🏢 방산기업", "value": companies_str, "inline": True},
                    {"name": "📰 언론사", "value": item.source, "inline": True},
                    {"name": "⏰ 발행시각", "value": item.published_at, "inline": True}
                ],
                "footer": {
                    "text": "국방·방산 뉴스 알리미 | DefenseNewsBot",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/9839/9839460.png"
                }
            }
        ]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DefenseNewsBot-GitHubActions"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Discord Error] 전송 실패: {e}")
        return False


async def run_cron():
    discord_webhook_raw = os.getenv("DISCORD_WEBHOOK_URL", "").strip() or Config.DISCORD_WEBHOOK_URL
    discord_webhooks = [u.strip() for u in discord_webhook_raw.replace("\n", ",").split(",") if u.strip()]
    has_kakao = bool(Config.KAKAO_REST_API_KEY and Config.KAKAO_REFRESH_TOKEN)

    if not discord_webhooks and not has_kakao:
        print("❌ [Error] 알림 대상이 설정되지 않았습니다.")
        print("DISCORD_WEBHOOK_URL 또는 KAKAO_REFRESH_TOKEN 설정을 확인해주세요.")
        sys.exit(1)

    print("=" * 60)
    print("🛡️ 국방·방산 뉴스 크롤러 & 브로드캐스터 시작")
    print(f"• 디스코드 알림 : {'✅ 활성화 (' + str(len(discord_webhooks)) + '개 웹훅 채널)' if discord_webhooks else '❌ 비활성화'}")
    print(f"• 카카오톡 알림 : {'✅ 활성화 (나와의 채팅)' if has_kakao else '❌ 비활성화'}")
    print("=" * 60)

    # 1. 새 뉴스 확인 (최대 5건)
    unseen_items = await news_service.get_unseen_news(limit=Config.MAX_ARTICLES_PER_CHECK)

    if not unseen_items:
        print("✅ 새로 발견된 국방/방산 뉴스가 없습니다. (이미 최신 상태)")
        return

    print(f"📢 {len(unseen_items)}건의 새로운 국방/방산 뉴스를 감지했습니다!")

    # 2. 각 기사 전송
    for idx, item in enumerate(unseen_items, 1):
        print(f"\n[{idx}/{len(unseen_items)}] {item.badge} {item.title}")

        # A. 디스코드 다중 웹훅 전송
        for w_idx, webhook_url in enumerate(discord_webhooks, 1):
            d_ok = send_article_to_discord(webhook_url, item)
            print(f"  └ [디스코드 채널 #{w_idx}] {'성공' if d_ok else '실패'}")

        # B. 카카오톡 전송
        if has_kakao:
            k_ok = kakao_sender.send_news_item(item)
            print(f"  └ [카카오톡] {'성공' if k_ok else '실패'}")

        await asyncio.sleep(1)  # 속도 제한 방지

    print("\n🎉 모든 알림 전송 처리가 완료되었습니다.")


if __name__ == "__main__":
    asyncio.run(run_cron())

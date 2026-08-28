"""
GitHub Actions 및 스케줄러 전용 웹훅 뉴스 브로드캐스터 (webhook_cron.py)
- 환경변수 DISCORD_WEBHOOK_URL을 읽어 새로운 국방/방산 뉴스를 디스코드 채널로 전송합니다.
- SQLite DB(data/news.db)에 전송 이력을 기록하여 중복 전송을 완벽히 방지합니다.
"""

import os
import sys
import asyncio
import json
import urllib.request
from typing import List

# Windows/Linux 콘솔 인코딩 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.config import Config
from src.services.news_service import news_service
from src.collectors.base import NewsItem
from src.services.embed_builder import CATEGORY_COLORS


def send_article_to_webhook(webhook_url: str, item: NewsItem) -> bool:
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
        print(f"[Webhook Error] 전송 실패: {e}")
        return False


async def run_cron():
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip() or Config.DISCORD_WEBHOOK_URL

    if not webhook_url:
        print("❌ [Error] DISCORD_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("GitHub 저장소의 Settings -> Secrets and variables -> Actions 에서 등록해주세요.")
        sys.exit(1)

    print("=" * 60)
    print("🛡️ GitHub Actions 국방·방산 뉴스 크롤러 시작")
    print("=" * 60)

    # 1. 새 뉴스 확인 (최대 5건)
    unseen_items = await news_service.get_unseen_news(limit=Config.MAX_ARTICLES_PER_CHECK)

    if not unseen_items:
        print("✅ 새로 발견된 국방/방산 뉴스가 없습니다. (이미 최신 상태)")
        return

    print(f"📢 {len(unseen_items)}건의 새로운 국방/방산 뉴스를 감지했습니다! 디스코드로 전송합니다...")

    # 2. 각 기사 웹훅 전송
    success_count = 0
    for idx, item in enumerate(unseen_items, 1):
        print(f"[{idx}/{len(unseen_items)}] {item.badge} {item.title}")
        success = send_article_to_webhook(webhook_url, item)
        if success:
            success_count += 1
            print("    └ 전송 성공!")
        else:
            print("    └ 전송 실패!")
        await asyncio.sleep(1)  # 디스코드 속도 제한 방지

    print(f"\n🎉 총 {success_count}/{len(unseen_items)}건의 뉴스를 성공적으로 전송 완료했습니다.")


if __name__ == "__main__":
    asyncio.run(run_cron())

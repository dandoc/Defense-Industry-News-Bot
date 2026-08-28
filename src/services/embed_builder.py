"""
디스코드 임베드(Embed) 메시지 빌더
- 기사별 카테고리/군종/기업 태그에 맞춘 컬러풀한 카드(Embed) 생성
- 다이제스트(브리핑) 임베드 생성
"""

import discord
from typing import List
from src.collectors.base import NewsItem

# 카테고리별 임베드 컬러 (Hex)
CATEGORY_COLORS = {
    "유도무기/방공": 0xE74C3C,      # 빨강
    "항공/우주/드론": 0x3498DB,      # 하늘색
    "기갑/화력/기동": 0x27AE60,      # 올리브/초록
    "함정/해양/잠수함": 0x1F4E79,    # 짙은 네이비
    "지휘통신/레이더/센서": 0x9B59B6,  # 보라색
    "해외수출/계약": 0xF1C40F,      # 골드/노랑
    "국방정책/전력화": 0x34495E,    # 다크 슬레이트
    "육군": 0x4B6F44,              # 국방색
    "해군": 0x003366,              # 해군블루
    "공군": 0x4A90E2,              # 공군블루
    "일반국방": 0x5865F2            # 디스코드 블루
}


class EmbedBuilder:
    @staticmethod
    def get_embed_color(category: str) -> int:
        return CATEGORY_COLORS.get(category, 0x5865F2)

    @classmethod
    def create_news_embed(cls, item: NewsItem) -> discord.Embed:
        """단일 뉴스 기사용 카드(Embed) 생성"""
        color = cls.get_embed_color(item.category)

        embed = discord.Embed(
            title=f"{item.badge} {item.title}",
            url=item.url,
            description=item.summary if item.summary else "기사 원문 링크를 클릭하여 전문을 확인하세요.",
            color=color
        )

        # 3차원 태그 필드 추가
        branches_str = " ".join(f"`{b}`" for b in item.branches) if item.branches else "`전군/공통`"
        domains_str = " ".join(f"`{d}`" for d in item.domains) if item.domains else "`종합방산`"
        companies_str = " ".join(f"`{c}`" for c in item.companies) if item.companies else "`정부/기타`"

        embed.add_field(name="🪖 군종", value=branches_str, inline=True)
        embed.add_field(name="🔬 산업분야", value=domains_str, inline=True)
        embed.add_field(name="🏢 관련기업", value=companies_str, inline=True)

        embed.add_field(name="📰 언론사", value=item.source, inline=True)
        embed.add_field(name="⏰ 발행시각", value=item.published_at, inline=True)

        if item.image_url:
            embed.set_thumbnail(url=item.image_url)

        embed.set_footer(text="국방·방산 뉴스 알리미 | DefenseNewsBot", icon_url="https://cdn-icons-png.flaticon.com/512/9839/9839460.png")
        return embed

    @classmethod
    def create_digest_embed(cls, items: List[NewsItem], title: str = "📋 국방·방산 최신 뉴스 브리핑") -> discord.Embed:
        """여러 기사를 한 번에 모아서 보여주는 다이제스트 Embed 생성"""
        embed = discord.Embed(
            title=title,
            description=f"총 **{len(items)}건**의 최신 국방 및 방위산업 소식을 전해드립니다.\n" + ("─" * 30),
            color=0x2B2D31
        )

        for idx, item in enumerate(items, 1):
            tags = []
            if item.branches:
                tags.append("🪖 " + " ".join(f"`{b}`" for b in item.branches))
            if item.domains:
                tags.append("🔬 " + " ".join(f"`{d}`" for d in item.domains))
            if item.companies:
                tags.append("🏢 " + " ".join(f"`{c}`" for c in item.companies))

            tags_line = " | ".join(tags) if tags else "`일반국방`"

            value_text = f"**출처**: {item.source} · {item.published_at}\n**태그**: {tags_line}\n👉 [기사 보러가기]({item.url})"
            embed.add_field(
                name=f"{idx}. {item.title}",
                value=value_text,
                inline=False
            )

        embed.set_footer(text="국방·방산 뉴스 알리미 | DefenseNewsBot")
        return embed

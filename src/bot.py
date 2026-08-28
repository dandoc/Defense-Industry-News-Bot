"""
디스코드 국방·방산 뉴스 알리미 봇 메인 실행 파일 (src/bot.py)
- 디스코드 봇 및 슬래시 커맨드 핸들러
- 백그라운드 뉴스 자동 감지 및 채널 브로드캐스트 루프
"""

import sys
import asyncio
from datetime import datetime
from typing import Optional

# Windows 콘솔 인코딩 UTF-8 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.config import Config
from src.db import db
from src.services.news_service import news_service
from src.services.embed_builder import EmbedBuilder


class DefenseNewsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """봇 기동 시 슬래시 커맨드 동기화 및 백그라운드 태스크 시작"""
        print("[Bot] Registering slash commands...")
        await self.tree.sync()
        print("[Bot] Slash commands synced successfully!")

        # 백그라운드 뉴스 확인 루프 시작
        if not self.check_news_loop.is_running():
            self.check_news_loop.change_interval(minutes=Config.CHECK_INTERVAL_MINUTES)
            self.check_news_loop.start()

    async def on_ready(self):
        print(f"[Bot] Logged in as {self.user} (ID: {self.user.id})")
        print(f"[Bot] Connected to {len(self.guilds)} guilds")
        
        # 봇 상태 메시지 설정
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="실시간 국방·방산 뉴스 모니터링"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    @tasks.loop(minutes=15)
    async def check_news_loop(self):
        """주기적으로 새 뉴스를 수집하여 등록된 채널로 전송"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new defense news...")
        try:
            new_articles = await news_service.get_unseen_news(limit=Config.MAX_ARTICLES_PER_CHECK)
            if not new_articles:
                print("[Bot] No new articles found.")
                return

            print(f"[Bot] Found {len(new_articles)} new article(s)! Broadcasting...")

            # 1. DB에 등록된 활성 채널 목록
            active_channels = db.get_all_active_channels()
            target_channel_ids = {int(ch["channel_id"]) for ch in active_channels}

            # 2. .env에 기본 설정된 채널 ID가 있다면 포함
            if Config.DISCORD_CHANNEL_ID:
                target_channel_ids.add(Config.DISCORD_CHANNEL_ID)

            if not target_channel_ids:
                print("[Bot] Warning: No target channels configured. Use /알림설정 채널 to register.")
                return

            # 각 채널로 임베드 전송
            for channel_id in target_channel_ids:
                channel = self.get_channel(channel_id)
                if not channel:
                    try:
                        channel = await self.fetch_channel(channel_id)
                    except Exception:
                        channel = None

                if channel:
                    for article in new_articles:
                        embed = EmbedBuilder.create_news_embed(article)
                        try:
                            await channel.send(embed=embed)
                            await asyncio.sleep(0.5)  # 속도 조절
                        except Exception as e:
                            print(f"[Bot] Failed to send message to channel {channel_id}: {e}")
        except Exception as e:
            print(f"[Bot Error] News check loop encountered error: {e}")

    @check_news_loop.before_loop
    async def before_check_news_loop(self):
        await self.wait_until_ready()


bot = DefenseNewsBot()


# ============================================================
# 슬래시 커맨드 정의 (Slash Commands)
# ============================================================

@bot.tree.command(name="뉴스_최신", description="최신 국방·방산 뉴스를 즉시 조회합니다.")
@app_commands.describe(개수="가져올 뉴스 개수 (기본값: 5, 최대: 10)")
async def news_latest(interaction: discord.Interaction, 개수: Optional[int] = 5):
    await interaction.response.defer(thinking=True)
    count = min(max(개수 or 5, 1), 10)

    articles = await news_service.fetch_all_news(limit=count)
    if not articles:
        await interaction.followup.send("❌ 최신 국방/방산 뉴스를 불러오지 못했습니다.", ephemeral=True)
        return

    embed = EmbedBuilder.create_digest_embed(articles, title=f"📋 최신 국방·방산 뉴스 ({len(articles)}건)")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="뉴스_검색", description="특정 키워드(예: KF-21, 천궁, 폴란드, 현대로템 등)로 뉴스를 검색합니다.")
@app_commands.describe(키워드="검색할 국방/방산 키워드")
async def news_search(interaction: discord.Interaction, 키워드: str):
    await interaction.response.defer(thinking=True)

    articles = await news_service.search_news(query=키워드, limit=5)
    if not articles:
        await interaction.followup.send(f"🔍 '{키워드}' 관련 최신 뉴스를 찾을 수 없습니다.", ephemeral=True)
        return

    embed = EmbedBuilder.create_digest_embed(articles, title=f"🔍 '{키워드}' 검색 결과 ({len(articles)}건)")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="브리핑", description="오늘의 주요 국방·방산 헤드라인 종합 브리핑을 출력합니다.")
async def news_briefing(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    articles = await news_service.fetch_all_news(limit=8)
    if not articles:
        await interaction.followup.send("❌ 브리핑할 뉴스를 찾지 못했습니다.", ephemeral=True)
        return

    embed = EmbedBuilder.create_digest_embed(articles, title="🪖 오늘의 국방·방산 주요 소식 다이제스트")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="알림설정_채널", description="실시간 국방·방산 뉴스 알림을 자동으로 수신할 채널을 설정합니다.")
@app_commands.describe(채널="알림을 받을 텍스트 채널")
@app_commands.checks.has_permissions(manage_channels=True)
async def set_channel(interaction: discord.Interaction, 채널: discord.TextChannel):
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.response.send_message("❌ 서버 내에서만 설정할 수 있습니다.", ephemeral=True)
        return

    db.set_guild_channel(guild_id=guild_id, channel_id=채널.id, interval_minutes=Config.CHECK_INTERVAL_MINUTES)
    await interaction.response.send_message(
        f"✅ 성공적으로 뉴스 알림 채널을 {채널.mention}(으)로 설정했습니다!\n"
        f"앞으로 {Config.CHECK_INTERVAL_MINUTES}분 주기로 새 국방·방산 뉴스가 자동 전송됩니다.",
        ephemeral=False
    )


@bot.tree.command(name="알림설정_상태", description="현재 서버의 국방·방산 뉴스 알림 설정 상태를 확인합니다.")
async def settings_status(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.response.send_message("❌ 서버 내에서만 확인할 수 있습니다.", ephemeral=True)
        return

    settings = db.get_guild_settings(guild_id)
    if not settings or not settings.get("enabled"):
        await interaction.response.send_message(
            "⚠️ 현재 서버에는 설정된 알림 채널이 없습니다.\n`/알림설정_채널` 명령어로 알림 채널을 등록해주세요.",
            ephemeral=True
        )
        return

    channel_id = int(settings["channel_id"])
    channel = interaction.guild.get_channel(channel_id)
    channel_mention = channel.mention if channel else f"ID: {channel_id}"

    embed = discord.Embed(title="⚙️ 국방·방산 뉴스 알림 설정 상태", color=0x5865F2)
    embed.add_field(name="📢 수신 채널", value=channel_mention, inline=True)
    embed.add_field(name="⏱️ 확인 주기", value=f"{settings.get('interval_minutes', 15)}분", inline=True)
    embed.add_field(name="🟢 활성화 여부", value="활성화됨" if settings.get("enabled") else "비활성화됨", inline=True)
    embed.set_footer(text="태그 분류: 🪖 군종 | 🔬 산업분야 | 🏢 방산기업")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="도움말", description="국방·방산 뉴스 봇의 사용법과 명령어 목록을 확인합니다.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ 국방·방산 뉴스 알리미 봇 도움말",
        description="대한민국 국방부, 방위사업청, K-방산 주요 기업(한화, KAI, LIG넥스원, 현대로템 등)의 최신 뉴스를 실시간으로 전달합니다.",
        color=0x5865F2
    )
    embed.add_field(
        name="📌 일반 명령어",
        value=(
            "`/뉴스_최신 [개수]` : 최신 국방/방산 뉴스 목록 조회\n"
            "`/뉴스_검색 [키워드]` : 특정 무기체계/기업/국가 키워드 검색\n"
            "`/브리핑` : 오늘의 주요 국방/방산 헤드라인 종합 다이제스트\n"
            "`/도움말` : 봇 사용법 및 기능 안내"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ 관리자 명령어",
        value=(
            "`/알림설정_채널 [채널]` : 자동 알림을 수신할 채널 지정\n"
            "`/알림설정_상태` : 현재 서버의 알림 설정 조회"
        ),
        inline=False
    )
    embed.add_field(
        name="🏷️ 3차원 태그 분류 시스템",
        value=(
            "• 🪖 **군종**: 육군, 해군, 공군, 해병대, 우주/사이버, 국방부/방사청\n"
            "• 🔬 **산업분야**: 유도무기/방공, 항공/우주/드론, 기갑/화력/기동, 함정/해양, 지휘통신/레이더, 방산수출/계약\n"
            "• 🏢 **방산기업**: 한화에어로스페이스, KAI, LIG넥스원, 현대로템, HD현대중공업, 풍산 등"
        ),
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


def main():
    token = Config.DISCORD_TOKEN
    if not token:
        print("[Error] DISCORD_TOKEN이 설정되지 않았습니다. .env 파일에 봇 토큰을 입력해주세요.")
        print("참고: .env.example 파일을 .env로 복사한 뒤 토큰을 입력하세요.")
        sys.exit(1)

    print("[Bot] Starting DefenseNewsBot...")
    bot.run(token)


if __name__ == "__main__":
    main()

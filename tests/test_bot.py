"""
국방·방산 뉴스 봇 단위 테스트 (Unit Tests)
- 뉴스 수집 데이터 모델 검증
- 3차원 태그 분류 엔진 검증 (군종, 산업분야, 방산기업)
- SQLite DB 중복 방지 및 설정 저장 검증
- Discord Embed 빌더 생성 검증
"""

import unittest
import os
import shutil
import tempfile
from pathlib import Path

from src.collectors.base import NewsItem
from src.services.news_service import NewsService
from src.services.embed_builder import EmbedBuilder
from src.db import Database


class TestDefenseNewsBot(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_news.db"
        self.db = Database(db_path=str(self.db_path))
        self.news_service = NewsService()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_news_item_id_generation(self):
        """NewsItem 고유 ID 생성 및 포맷팅 검증"""
        item = NewsItem(
            title="폴란드, K2 전차 2차 이행계약 체결 임박",
            url="https://example.com/k2-poland-contract",
            source="국방일보"
        )
        self.assertTrue(len(item.id) > 0)
        self.assertEqual(item.source, "국방일보")

    def test_three_dimensional_tag_classification(self):
        """3차원 태그 (군종, 산업분야, 방산기업) 분류 검증"""
        # 1. K2 전차 / 현대로템 / 폴란드 수출 기사
        item1 = NewsItem(
            title="현대로템, 폴란드와 K2 전차 추가 수출 계약 협상 순항",
            url="https://example.com/item1",
            summary="육군 주력 전차인 K2 흑표가 폴란드 현지 생산형 공급을 위해..."
        )
        classified1 = self.news_service.classify_article(item1)
        self.assertIn("육군", classified1.branches)
        self.assertIn("기갑/화력/기동", classified1.domains)
        self.assertIn("해외수출/계약", classified1.domains)
        self.assertIn("현대로템", classified1.companies)

        # 2. KF-21 / KAI / 공군 기사
        item2 = NewsItem(
            title="한국항공우주(KAI), 공군 차세대 전투기 KF-21 양산 1호기 조립 착수",
            url="https://example.com/item2",
            summary="AESA 레이더와 최첨단 항공전자 장비를 탑재한 대한민국 공군의 KF-21..."
        )
        classified2 = self.news_service.classify_article(item2)
        self.assertIn("공군", classified2.branches)
        self.assertIn("항공/우주/드론", classified2.domains)
        self.assertIn("KAI(한국항공우주)", classified2.companies)

        # 3. 천궁-II / LIG넥스원 / 유도무기 기사
        item3 = NewsItem(
            title="LIG넥스원, 천궁-II 요격 미사일 중동 수출 추가 수주 유력",
            url="https://example.com/item3",
            summary="탄도탄 요격 방공체계인 천궁-II의 해외 러브콜이 이어지고 있다."
        )
        classified3 = self.news_service.classify_article(item3)
        self.assertIn("유도무기/방공", classified3.domains)
        self.assertIn("해외수출/계약", classified3.domains)
        self.assertIn("LIG넥스원", classified3.companies)

        # 4. 해군 잠수함 / 한화오션 기사
        item4 = NewsItem(
            title="한화오션, 해군 도산안창호급 3000톤급 장보고-III 잠수함 진수",
            url="https://example.com/item4",
            summary="해군 최신예 전략 유도탄 탑재 잠수함의 성공적 건조..."
        )
        classified4 = self.news_service.classify_article(item4)
        self.assertIn("해군", classified4.branches)
        self.assertIn("함정/해양/잠수함", classified4.domains)
        self.assertIn("한화오션", classified4.companies)

    def test_database_deduplication(self):
        """SQLite 중복 저장 방지 및 조회 검증"""
        item = NewsItem(
            title="방위사업청, 차세대 호위함 사업설명회 개최",
            url="https://example.com/dapa-frigate",
            source="방위사업청"
        )
        # 처음에는 미전송 상태
        self.assertFalse(self.db.is_article_sent(item.id, item.url))

        # 전송 완료 기록
        success = self.db.mark_article_sent(
            article_id=item.id,
            url=item.url,
            title=item.title,
            source=item.source,
            category=item.category,
            published_at=item.published_at
        )
        self.assertTrue(success)

        # 재확인 시 전송 완료 상태여야 함
        self.assertTrue(self.db.is_article_sent(item.id, item.url))

        # 중복 insert 시도 시 에러 없이 통과
        dup_success = self.db.mark_article_sent(
            article_id=item.id,
            url=item.url,
            title=item.title
        )
        self.assertFalse(dup_success)  # INSERT OR IGNORE 로 rowcount 0

    def test_guild_settings_storage(self):
        """서버별 알림 채널 저장 및 조회 검증"""
        guild_id = 9988776655
        channel_id = 1122334455

        self.db.set_guild_channel(guild_id=guild_id, channel_id=channel_id, interval_minutes=20)
        settings = self.db.get_guild_settings(guild_id=guild_id)

        self.assertIsNotNone(settings)
        self.assertEqual(settings["channel_id"], str(channel_id))
        self.assertEqual(settings["interval_minutes"], 20)
        self.assertEqual(settings["enabled"], 1)

    def test_embed_builder(self):
        """Discord Embed 빌더 생성 검증"""
        item = NewsItem(
            title="한화에어로스페이스, 루마니아 K9 자주포 공급 계약 완료",
            url="https://example.com/k9-romania",
            source="연합뉴스",
            summary="한화에어로스페이스가 1조원 규모의 루마니아 K9 자주포 및 K10 탄약운반차 수출 계약을 완료했다.",
            branches=["육군"],
            domains=["기갑/화력/기동", "해외수출/계약"],
            companies=["한화에어로스페이스"]
        )
        embed = EmbedBuilder.create_news_embed(item)
        self.assertIsNotNone(embed)
        self.assertIn("한화에어로스페이스", embed.title)
        self.assertEqual(len(embed.fields), 5)  # 군종, 산업분야, 관련기업, 언론사, 발행시각


if __name__ == "__main__":
    unittest.main()

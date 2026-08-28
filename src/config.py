"""
설정 관리 모듈 (Configuration)
.env 파일 및 환경 변수를 로드하여 봇 전체에서 활용할 수 있도록 제공합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 루트 경로 기준 .env 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Config:
    # Discord 설정
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "").strip()
    DISCORD_CHANNEL_ID: int = int(os.getenv("DISCORD_CHANNEL_ID", "0")) if os.getenv("DISCORD_CHANNEL_ID", "").strip().isdigit() else 0
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    # 수집 및 스케줄링 설정
    CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
    MAX_ARTICLES_PER_CHECK: int = int(os.getenv("MAX_ARTICLES_PER_CHECK", "5"))

    # 데이터베이스 설정
    DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/news.db")

    # 추가 키워드 설정 (쉼표 구분)
    _raw_keywords = os.getenv("CUSTOM_KEYWORDS", "")
    CUSTOM_KEYWORDS: list[str] = [k.strip() for k in _raw_keywords.split(",") if k.strip()]

    # 네이버 API 설정 (선택 사항)
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "").strip()
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    # 기본 국방/방산 검색 쿼리 목록
    DEFAULT_QUERIES: list[str] = [
        '국방 OR 방산 OR 방위산업 OR "K-방산"',
        '한화에어로스페이스 OR LIG넥스원 OR 현대로템 OR 한국항공우주',
        '방위사업청 OR 국방부',
        'KF-21 OR "K2 전차" OR 천궁 OR 장보고'
    ]


# DB 디렉토리 자동 생성
Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

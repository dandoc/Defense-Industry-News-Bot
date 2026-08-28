"""
뉴스 데이터 모델 및 기본 수집기 인터페이스 정의
- 산업분야(domains), 군종(branches), 방산기업(companies) 태그 체계 지원
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib


class NewsItem(BaseModel):
    """표준 뉴스 아이템 모델 (다차원 태그 지원)"""
    id: str = Field(default="", description="고유 식별자 해시")
    title: str = Field(..., description="뉴스 제목")
    url: str = Field(..., description="기사 원문 URL")
    source: str = Field(default="국방뉴스", description="언론사 또는 출처")
    summary: str = Field(default="", description="기사 요약 또는 본문 일부")
    published_at: str = Field(default="", description="발행 시각 (ISO 또는 읽기 쉬운 형식)")
    
    # 3차원 태그 체계
    branches: List[str] = Field(default_factory=list, description="군종 태그 (육군, 해군, 공군, 해병대, 우주/사이버, 국방부/방사청 등)")
    domains: List[str] = Field(default_factory=list, description="산업/기술 분야 태그 (기갑, 항공, 유도무기, 함정, 지휘통신, 수출 등)")
    companies: List[str] = Field(default_factory=list, description="관련 방산 기업 태그 (한화, KAI, LIG넥스원, 현대로템 등)")

    # 기본 레거시 호환용 필드
    category: str = Field(default="일반국방", description="대표 카테고리")
    badge: str = Field(default="🛡️ [국방·방산]", description="대표 뱃지")
    image_url: Optional[str] = Field(default=None, description="기사 대표 이미지 URL")

    def model_post_init(self, __context):
        if not self.id:
            content = f"{self.url.strip()}_{self.title.strip()}"
            self.id = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not self.published_at:
            self.published_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    @property
    def formatted_tags_display(self) -> str:
        """디스코드 임베드에 표시할 포맷팅된 태그 문자열"""
        parts = []
        if self.branches:
            parts.append(f"🪖 {' '.join(f'`{b}`' for b in self.branches)}")
        if self.domains:
            parts.append(f"🔬 {' '.join(f'`{d}`' for d in self.domains)}")
        if self.companies:
            parts.append(f"🏢 {' '.join(f'`{c}`' for c in self.companies)}")

        return " | ".join(parts) if parts else "`일반국방`"


class BaseNewsCollector(ABC):
    """뉴스 수집기 추상 기본 클래스"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def fetch_news(self, query: Optional[str] = None, limit: int = 10) -> List[NewsItem]:
        pass

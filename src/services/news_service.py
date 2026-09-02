"""
뉴스 서비스 (NewsService)
- 다중 수집기(Google News, DAPA, Naver)로부터 뉴스를 통합 수집
- 3차원 태그 분류 엔진: [군종], [산업/기술분야], [방산기업]
- SQLite 데이터베이스와 연동하여 중복 기사 필터링 및 관리
"""

import asyncio
import re
from typing import List, Optional, Set
from src.collectors.base import NewsItem, BaseNewsCollector
from src.collectors.google_news import GoogleNewsCollector
from src.collectors.dapa_news import DapaNewsCollector
from src.collectors.naver_news import NaverNewsCollector
from src.db import db
from src.config import Config


# 1. 군종 (Military Branch) 매핑 규칙
BRANCH_RULES = {
    "육군": ["육군", "지상군", "보병", "기갑", "포병", "특전사", "K2전차", "K2 전차", "흑표", "K9", "K-9", "자주포", "레드백", "천무", "K21", "워리어플랫폼"],
    "해군": ["해군", "함대", "잠수함", "호위함", "구축함", "이지스", "도산안창호", "장보고", "상륙함", "수상함", "군함", "KDDX", "FFX", "UDT", "해난구조대"],
    "공군": ["공군", "비행단", "전투기", "KF-21", "FA-50", "T-50", "수리온", "LAH", "F-35", "F-15", "공중급유기", "조기경보기", "방공관제"],
    "해병대": ["해병대", "상륙장갑차", "KAAV", "상륙작전"],
    "우주/사이버": ["우주군", "우주사령부", "정찰위성", "군사위성", "사이버작전", "사이버사령부", "전자전"],
    "국방부/방사청": ["국방부", "방위사업청", "방사청", "합동참모본부", "합참", "국방과학연구소", "ADD", "국방기술품질원", "기품원"]
}

# 2. 산업/기술 분야 (Industry Domain) 매핑 규칙
DOMAIN_RULES = {
    "유도무기/방공": ["천궁", "미사일", "현무", "비궁", "해궁", "L-SAM", "M-SAM", "신궁", "유도탄", "패트리어트", "탄도탄", "방공", "요격", "다련장", "발사대"],
    "항공/우주/드론": ["KF-21", "FA-50", "T-50", "수리온", "LAH", "전투기", "헬기", "항공기", "무인기", "드론", "AESA", "우주항공", "발사체", "UAM", "위성"],
    "기갑/화력/기동": ["K2", "K-2", "흑표", "K9", "자주포", "천무", "장갑차", "레드백", "K21", "전차", "차륜형", "자주도하", "화포", "탄약", "자주발사대"],
    "함정/해양/잠수함": ["잠수함", "호위함", "구축함", "장보고", "도산안창호", "이지스함", "함정", "수상함", "무인수상정", "USV", "UUV", "KDDX", "FFX"],
    "지휘통신/레이더/센서": ["레이더", "TICN", "C4I", "소나", "전자광학", "EO/IR", "감시정찰", "군위성통신", "지휘통제", "센서", "통신망"],
    "해외수출/계약": ["수출", "계약", "수주", "폴란드", "루마니아", "사우디", "호주", "UAE", "MRO", "K-방산", "글로벌", "방산수출", "절충교역", "도입계약"],
    "국방정책/전력화": ["전력화", "소요결정", "방추위", "국방개혁", "방위력개선비", "국방예산", "획득사업", "사업타당성"]
}

# 3. 방산 기업 (Defense Companies) 매핑 규칙
COMPANY_RULES = {
    "한화에어로스페이스": ["한화에어로스페이스", "한화에어로"],
    "한화시스템": ["한화시스템"],
    "한화오션": ["한화오션"],
    "KAI(한국항공우주)": ["한국항공우주산업", "한국항공우주", "KAI"],
    "LIG D&A": ["LIG D&A", "LIG디앤에이", "LIG D&A", "LIG넥스원", "LIG 넥스원", "넥스원", "엘아이지디앤에이"],
    "현대로템": ["현대로템", "로템"],
    "현대자동차": ["현대자동차", "현대차", "Hyundai Motor"],
    "HD현대중공업": ["HD현대중공업", "HD현대", "현대중공업"],
    "LG이노텍": ["LG이노텍", "LG 이노텍", "LG Innotek"],
    "풍산": ["풍산", "POONGSAN"],
    "대한항공": ["대한항공 항공우주", "대한항공"],
    "SNT모티브/다이내믹스": ["SNT모티브", "SNT다이내믹스", "SNT중공업"],
    "기타/글로벌방산": ["록히드마틴", "보잉", "레이시온", "BAE", "라인메탈", "사브", "탈레스"]
}


class NewsService:
    def __init__(self):
        self.collectors: List[BaseNewsCollector] = [
            GoogleNewsCollector(),
            DapaNewsCollector(),
            NaverNewsCollector()
        ]

    @staticmethod
    def _match_keywords(text: str, keywords: List[str]) -> bool:
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                return True
        return False

    def classify_article(self, item: NewsItem) -> NewsItem:
        """
        기사 제목과 본문을 분석하여 군종(branch), 산업분야(domain), 방산기업(company) 태그를 추출합니다.
        """
        full_text = f"{item.title} {item.summary}"

        # 1. 군종 추출
        matched_branches: Set[str] = set()
        for branch, kws in BRANCH_RULES.items():
            if self._match_keywords(full_text, kws):
                matched_branches.add(branch)

        # 2. 산업분야 추출
        matched_domains: Set[str] = set()
        for domain, kws in DOMAIN_RULES.items():
            if self._match_keywords(full_text, kws):
                matched_domains.add(domain)

        # 3. 방산기업 추출
        matched_companies: Set[str] = set()
        for company, kws in COMPANY_RULES.items():
            if self._match_keywords(full_text, kws):
                matched_companies.add(company)

        # 결과 할당 (순서 정렬)
        item.branches = sorted(list(matched_branches))
        item.domains = sorted(list(matched_domains))
        item.companies = sorted(list(matched_companies))

        # 대표 카테고리 및 대표 뱃지 설정
        if item.domains:
            primary_domain = item.domains[0]
            item.category = primary_domain
            badge_map = {
                "유도무기/방공": "🚀 [유도무기/방공]",
                "항공/우주/드론": "✈️ [항공/우주/드론]",
                "기갑/화력/기동": "🛡️ [기갑/화력/기동]",
                "함정/해양/잠수함": "🚢 [함정/해양/잠수함]",
                "지휘통신/레이더/센서": "📡 [지휘통신/레이더]",
                "해외수출/계약": "🌐 [방산수출/계약]",
                "국방정책/전력화": "📢 [국방정책/공식]"
            }
            item.badge = badge_map.get(primary_domain, f"🛡️ [{primary_domain}]")
        elif item.branches:
            primary_branch = item.branches[0]
            item.category = primary_branch
            item.badge = f"🪖 [{primary_branch}]"
        else:
            item.category = "일반국방"
            item.badge = "🛡️ [국방·방산]"

        return item

    @staticmethod
    def is_target_company_article(item: NewsItem) -> bool:
        """타겟 기업이 설정된 경우, 해당 기업으로 분류된 기사만 통과시킵니다."""
        if not Config.TARGET_COMPANIES:
            return True
        target_companies = set()
        for configured_name in Config.TARGET_COMPANIES:
            configured_key = configured_name.casefold()
            for canonical_name, aliases in COMPANY_RULES.items():
                if configured_key == canonical_name.casefold() or any(configured_key == alias.casefold() for alias in aliases):
                    target_companies.add(canonical_name.casefold())
                    break
            else:
                target_companies.add(configured_key)

        return any(company.casefold() in target_companies for company in item.companies)

    @staticmethod
    def is_industry_core_article(item: NewsItem) -> bool:
        """방산업계 의사결정에 직접 영향을 주는 핵심 신호인지 판별합니다."""
        if "해외수출/계약" in item.domains:
            return True
        core_signals = [
            "수주", "계약", "입찰", "사업자 선정", "우선협상", "양산", "인도",
            "전력화", "방위력개선", "방추위", "획득사업", "국방예산", "MRO",
            "공급망", "합작", "기술협력", "수출"
        ]
        full_text = f"{item.title} {item.summary}"
        return NewsService._match_keywords(full_text, core_signals)

    def _article_priority(self, item: NewsItem) -> int:
        """기업 타겟과 업계 핵심 신호를 기준으로 발송 우선순위를 산정합니다."""
        score = 0
        if self.is_target_company_article(item):
            score += 100
        if self.is_industry_core_article(item):
            score += 50
        return score

    async def fetch_all_news(self, query: Optional[str] = None, limit: int = 15) -> List[NewsItem]:
        """모든 수집기로부터 뉴스 병렬 수집 및 다차원 태깅"""
        tasks = [collector.fetch_news(query=query, limit=limit) for collector in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: List[NewsItem] = []
        seen_ids = set()

        for res in results:
            if isinstance(res, list):
                for item in res:
                    if item.id not in seen_ids:
                        seen_ids.add(item.id)
                        classified = self.classify_article(item)
                        all_items.append(classified)
            elif isinstance(res, Exception):
                print(f"[NewsService] Collector error: {res}")

        # 사용자 지정 커스텀 키워드가 있는 경우 추가 쿼리 수집
        if not query and Config.CUSTOM_KEYWORDS:
            for kw in Config.CUSTOM_KEYWORDS:
                try:
                    gc = GoogleNewsCollector()
                    kw_items = await gc.fetch_news(query=kw, limit=3)
                    for item in kw_items:
                        if item.id not in seen_ids:
                            seen_ids.add(item.id)
                            all_items.append(self.classify_article(item))
                except Exception as e:
                    print(f"[NewsService] Custom keyword '{kw}' fetch failed: {e}")

        # 타겟 기업은 기본 검색어에 빠질 수 있으므로 기업명으로도 별도 수집합니다.
        if not query and Config.TARGET_COMPANIES:
            for company in Config.TARGET_COMPANIES:
                try:
                    # 일반 기업 뉴스가 섞이지 않도록 방산 관련 신호와 함께 검색합니다.
                    company_query = f'{company} (방산 OR 방위산업 OR 국방 OR 군용 OR MRO OR 방산수출)'
                    company_items = await GoogleNewsCollector().fetch_news(query=company_query, limit=5)
                    for item in company_items:
                        if item.id not in seen_ids:
                            seen_ids.add(item.id)
                            all_items.append(self.classify_article(item))
                except Exception as e:
                    print(f"[NewsService] Target company '{company}' fetch failed: {e}")

            if Config.TARGET_COMPANY_MODE == "only":
                all_items = [item for item in all_items if self.is_target_company_article(item)]
            else:
                # 기본 모드: 지정 기업 뉴스와 방산업계 핵심 신호를 함께 남깁니다.
                all_items = [
                    item for item in all_items
                    if self.is_target_company_article(item) or self.is_industry_core_article(item)
                ]

        # 타겟 기업 > 업계 핵심 신호 > 발행시각 순으로 정렬
        all_items.sort(key=lambda x: (self._article_priority(x), x.published_at), reverse=True)
        return all_items[:limit]

    async def get_unseen_news(self, limit: int = 5) -> List[NewsItem]:
        """아직 전송되지 않은 새 기사를 선별합니다.

        전송 이력 기록은 호출자가 실제 전송에 성공한 뒤 수행해야 합니다.
        그렇지 않으면 일시적인 발송 실패가 영구 누락으로 이어집니다.
        """
        all_news = await self.fetch_all_news(limit=25)
        unseen: List[NewsItem] = []

        for item in all_news:
            if not db.is_article_sent(item.id, item.url):
                unseen.append(item)
                if len(unseen) >= limit:
                    break

        return unseen

    async def search_news(self, query: str, limit: int = 5) -> List[NewsItem]:
        """특정 키워드로 실시간 검색"""
        return await self.fetch_all_news(query=query, limit=limit)


# 전역 인스턴스
news_service = NewsService()

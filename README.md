# 🛡️ 국방·방산 뉴스 디스코드 알리미 봇 (DefenseNewsBot)

대한민국 국방부, 방위사업청, K-방산 주요 기업(한화, KAI, LIG넥스원, 현대로템 등), 무기체계 및 해외 방산 수출 소식을 실시간으로 수집하여 디스코드 채널에 깔끔한 카드(Embed) 형태로 전송해주는 디스코드 봇입니다.

---

## 🌟 주요 특징 및 기능

### 1. 🏷️ 3차원 다차원 태그 분류 시스템
수집된 뉴스를 **군종**, **산업/기술분야**, **방산기업** 3가지 축으로 정밀 자동 분석하여 태그를 부여합니다.

| 분류 축 | 포함 카테고리 | 예시 |
| :--- | :--- | :--- |
| **🪖 군종 (Branch)** | 육군, 해군, 공군, 해병대, 우주/사이버, 국방부/방사청 | `[육군]`, `[공군]`, `[해군]` |
| **🔬 산업/기술분야 (Domain)** | 유도무기/방공, 항공/우주/드론, 기갑/화력/기동, 함정/해양, 지휘통신/레이더, 해외수출/계약, 국방정책/전력화 | `[기갑/화력/기동]`, `[해외수출/계약]` |
| **🏢 방산기업 (Company)** | 한화에어로스페이스, 한화시스템, 한화오션, KAI(한국항공우주), LIG넥스원, 현대로템, HD현대중공업, 풍산, 대한항공 등 | `[한화에어로스페이스]`, `[현대로템]` |

### 2. ⚡ 다중 소스 수집 및 중복 방지
- **Google News RSS (Korean)**: 국방, 방산, K-방산 실시간 뉴스 스트림
- **방위사업청(DAPA) / 국방부(MND)**: 공식 보도자료 및 정책 발표
- **네이버 뉴스 검색 API**: 고속 키워드 검색 지원 (선택)
- **SQLite 캐싱**: 전송 이력을 로컬 DB에 기록하여 동일 기사의 중복 알림을 원천 차단

### 3. 🤖 디스코드 슬래시 커맨드 (Slash Commands)
- `/뉴스_최신 [개수]` : 최근 수집된 국방·방산 뉴스 목록 카드 확인
- `/뉴스_검색 [키워드]` : 특정 무기체계나 기업(예: `KF-21`, `천궁`, `폴란드`, `잠수함`) 검색
- `/브리핑` : 오늘의 국방/방산 주요 뉴스 종합 다이제스트 즉시 전송
- `/알림설정_채널 [채널]` : 뉴스를 실시간으로 자동 수신할 디스코드 채널 지정
- `/알림설정_상태` : 현재 서버의 알림 채널 및 설정 확인
- `/도움말` : 봇 사용법 및 태그 분류 안내

---

## 📁 프로젝트 구조

```
brave-archimedes/
├── .env.example              # 환경 변수 템플릿
├── .gitignore
├── requirements.txt          # Python 의존성 패키지
├── README.md                 # 프로젝트 가이드
├── standalone_broadcast.py   # 터미널 즉시 테스트 및 웹훅 전송용 스크립트
├── data/
│   └── news.db               # SQLite 전송 이력 및 서버 설정 DB (자동 생성)
├── tests/
│   └── test_bot.py           # 태그 분류 및 DB 로직 단위 테스트
└── src/
    ├── __init__.py
    ├── config.py             # 설정 로더
    ├── db.py                 # SQLite 데이터베이스 관리 모듈
    ├── bot.py                # 디스코드 봇 메인 실행 파일
    ├── collectors/           # 뉴스 수집 엔진
    │   ├── __init__.py
    │   ├── base.py           # NewsItem 모델 및 추상 클래스
    │   ├── google_news.py    # Google News RSS 수집기
    │   ├── dapa_news.py      # 방위사업청/국방부 보도자료 수집기
    │   └── naver_news.py     # 네이버 뉴스 수집기
    └── services/
        ├── __init__.py
        ├── news_service.py   # 3차원 태그 분류 및 중복 필터링 서비스
        └── embed_builder.py  # Discord Embed 카드 생성기
```

---

## 🚀 시작하기 (Setup & Run)

### 1. 사전 요구사항
- Python 3.10 이상

### 2. 가상환경 생성 및 패키지 설치
```bash
# 가상환경 생성 및 활성화
python -m venv .venv
# Windows:
.\.venv\Scripts\activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 3. 디스코드 봇 생성 및 토큰 발급 방법
1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속하여 로그인합니다.
2. 우측 상단 **New Application** 클릭 후 봇 이름을 입력합니다 (예: `DefenseNewsBot`).
3. 좌측 메뉴의 **Bot** 탭으로 이동:
   - **Reset Token**을 눌러 토큰을 복사합니다 (`DISCORD_TOKEN`).
   - 아래의 **Privileged Gateway Intents** 섹션에서:
     - `Message Content Intent` (활성화 권장)
4. 좌측 메뉴의 **OAuth2 -> URL Generator** 탭으로 이동:
   - **SCOPES**: `bot`, `applications.commands` 체크
   - **BOT PERMISSIONS**: `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `View Channels` 체크
   - 하단에 생성된 **Generated URL**을 복사하여 브라우저에 붙여넣고 내 디스코드 서버로 봇을 초대합니다.

### 4. 환경 변수 설정 (`.env`)
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 발급받은 토큰을 입력합니다.
```bash
cp .env.example .env
```

`.env` 설정 항목:
```env
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=123456789012345678    # 알림 받을 채널 ID (숫자)
CHECK_INTERVAL_MINUTES=15                 # 수집 주기 (기본: 15분)
MAX_ARTICLES_PER_CHECK=5                  # 1회 최대 발송 수
```

---

## 🏃 봇 실행

### 방법 1. 상시 디스코드 봇 구동 (슬래시 커맨드 및 자동 알림)
```bash
python -m src.bot
# 또는
python src/bot.py
```
> 봇이 켜지면 슬래시 커맨드가 자동 등록되며, `/알림설정_채널`로 지정된 채널에 15분마다 새 국방/방산 뉴스가 전송됩니다.

### 방법 2. 24시간 완전 무료 자동화 (GitHub Actions + 웹훅, 내 컴퓨터 꺼도 작동!)
> **컴퓨터 끄기 가능 / 서버 비용 0원 / 30분마다 자동 실행**

1. 디스코드에서 알림 받을 채널 우클릭 → `채널 편집` → `연동` → `웹후크` → **웹후크 URL 복사**
2. 이 프로젝트를 내 **GitHub 저장소(Private/Public)**에 푸시합니다.
3. GitHub 저장소 페이지의 `Settings` → `Secrets and variables` → `Actions` → **New repository secret** 클릭
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: 복사한 디스코드 웹후크 URL 입력
4. 이제 **GitHub 서버가 30분마다 알아서 뉴스를 수집해 디스코드로 쏴줍니다!**
   - GitHub Actions 탭에서 `국방·방산 뉴스 자동 알림` 워크플로우를 수동 실행(`Run workflow`)하여 바로 테스트할 수도 있습니다.

### 방법 3. 단독 테스트 및 로컬 웹훅 브로드캐스트
디스코드 봇 토큰 없이도 로컬에서 즉시 수집/태그를 테스트하거나 Webhook URL로 발송할 수 있습니다:
```bash
python standalone_broadcast.py
```

### 🧪 단위 테스트 실행
```bash
python -m unittest tests/test_bot.py
```

---

## 📸 디스코드 메시지 카드 예시
각 기사는 분야별 고유 색상과 3차원 태그 뱃지가 붙어 직관적으로 확인할 수 있습니다:
```
[✈️ 항공/우주/드론] 한국항공우주(KAI), 공군 차세대 전투기 KF-21 양산 1호기 최종 조립 착수
🪖 군종: `공군` | 🔬 산업분야: `항공/우주/드론` `해외수출/계약` | 🏢 관련기업: `KAI(한국항공우주)`
📰 언론사: 국방일보 | ⏰ 발행시각: 2026-08-28 14:00
👉 [기사 원문 바로가기](https://...)
```

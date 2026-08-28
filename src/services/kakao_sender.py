"""
카카오톡 '나에게 보내기' 메시지 전송 모듈 (KakaoSender)
- 카카오 오픈 API (REST API)를 사용하여 내 카카오톡(나와의 채팅)으로 국방/방산 뉴스 카드 전송
- Refresh Token 기반 Access Token 자동 갱신으로 만료 없이 24시간 연속 동작 지원
"""

import json
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any
from datetime import datetime

from src.collectors.base import NewsItem
from src.config import Config


class KakaoSender:
    AUTH_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    SEND_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

    def __init__(self, rest_api_key: Optional[str] = None, refresh_token: Optional[str] = None):
        self.rest_api_key = rest_api_key or Config.KAKAO_REST_API_KEY
        self.refresh_token = refresh_token or Config.KAKAO_REFRESH_TOKEN
        self.access_token: Optional[str] = None

    def refresh_access_token(self) -> Optional[str]:
        """Refresh Token을 이용해 새로운 Access Token 발급"""
        if not self.rest_api_key or not self.refresh_token:
            return None

        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_api_key,
            "refresh_token": self.refresh_token,
        }

        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            self.AUTH_TOKEN_URL,
            data=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self.access_token = result.get("access_token")
                # 신규 refresh_token이 함께 발급된 경우 갱신
                if result.get("refresh_token"):
                    self.refresh_token = result.get("refresh_token")
                return self.access_token
        except Exception as e:
            print(f"[KakaoSender] 토큰 갱신 실패: {e}")
            return None

    def send_news_item(self, item: NewsItem) -> bool:
        """단일 뉴스 기사를 카카오톡 '나에게 보내기(피드형)'로 전송"""
        if not self.access_token:
            token = self.refresh_access_token()
            if not token:
                print("[KakaoSender] Access Token 발급에 실패하여 카카오톡 전송을 건너뜁니다.")
                return False

        # 3차원 태그 문자열 구성
        tags = []
        if item.branches:
            tags.append(f"🪖 {' '.join(f'#{b}' for b in item.branches)}")
        if item.domains:
            tags.append(f"🔬 {' '.join(f'#{d}' for d in item.domains)}")
        if item.companies:
            tags.append(f"🏢 {' '.join(f'#{c}' for c in item.companies)}")

        tags_str = "\n".join(tags) if tags else "#국방 #방산"

        # 카카오톡 피드 템플릿 JSON
        description_text = f"{item.summary[:90]}..." if len(item.summary) > 90 else item.summary
        full_description = f"[{item.source} · {item.published_at}]\n{tags_str}\n\n{description_text}"

        template_object = {
            "object_type": "feed",
            "content": {
                "title": f"{item.badge} {item.title}",
                "description": full_description,
                "image_url": item.image_url or "https://cdn-icons-png.flaticon.com/512/9839/9839460.png",
                "image_width": 640,
                "image_height": 360,
                "link": {
                    "web_url": item.url,
                    "mobile_web_url": item.url
                }
            },
            "buttons": [
                {
                    "title": "📰 기사 전문 보러가기",
                    "link": {
                        "web_url": item.url,
                        "mobile_web_url": item.url
                    }
                }
            ]
        }

        return self._send_request(template_object)

    def _send_request(self, template_object: Dict[str, Any], retry: bool = True) -> bool:
        payload = urllib.parse.urlencode({
            "template_object": json.dumps(template_object, ensure_ascii=False)
        }).encode("utf-8")

        req = urllib.request.Request(
            self.SEND_MEMO_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            # 토큰 만료(401) 시 1회 재발급 후 재시도
            if e.code == 401 and retry:
                print("[KakaoSender] 토큰 만료 감지, 재발급 후 재시도...")
                if self.refresh_access_token():
                    return self._send_request(template_object, retry=False)
            print(f"[KakaoSender] HTTP 에러 ({e.code}): {e.read().decode('utf-8')}")
            return False
        except Exception as e:
            print(f"[KakaoSender] 전송 중 오류 발생: {e}")
            return False


kakao_sender = KakaoSender()

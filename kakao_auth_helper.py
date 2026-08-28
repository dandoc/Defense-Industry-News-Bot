"""
카카오톡 로그인 인증 도우미 (kakao_auth_helper.py)
- 내 개인 카카오톡으로 메시지를 보내기 위한 최초 토큰(Refresh Token)을 간편하게 발급받는 스크립트입니다.
- 브라우저를 열어 카카오 로그인을 진행하면 자동으로 Refresh Token을 생성하여 .env에 저장해줍니다.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# 콘솔 인코딩 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REDIRECT_PORT = 5000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth"
AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"

auth_code = None
server_instance = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/oauth":
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <html>
                <head><title>인증 완료</title></head>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: #2ECC71;">✅ 카카오 인증이 성공적으로 완료되었습니다!</h1>
                    <p>이 브라우저 창을 닫고 터미널(콘솔)로 돌아가세요.</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization code not found.")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 로깅 억제


def exchange_code_for_tokens(rest_api_key: str, code: str) -> dict:
    """인가 코드로 토큰 교환"""
    data = {
        "grant_type": "authorization_code",
        "client_id": rest_api_key,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 65)
    print("📱 카카오톡 '나에게 보내기' 최초 인증 도우미")
    print("=" * 65)

    # 1. REST API 키 입력 받기
    rest_api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not rest_api_key:
        print("\n[사전 준비]")
        print("1. https://developers.kakao.com/ 접속 및 로그인")
        print("2. [내 애플리케이션] -> [애플리케이션 추가하기] (이름: 국방방산알리미)")
        print("3. [앱 키] 메뉴에서 'REST API 키' 복사")
        print("4. [카카오 로그인] 메뉴 -> 활성화 설정 'ON' 클릭")
        print(f"5. [카카오 로그인] -> [Redirect URI 등록] 에 다음 주소 추가:")
        print(f"   👉  {REDIRECT_URI}")
        print("6. [카카오 로그인] -> [동의항목] -> '카카오톡 메시지 전송' 항목 설정 '이용 중 동의' 체크\n")
        
        rest_api_key = input("👉 카카오 [REST API 키]를 입력하세요: ").strip()

    if not rest_api_key:
        print("❌ REST API 키가 입력되지 않았습니다.")
        return

    # 2. 로컬 웹서버 시작
    global server_instance
    server_instance = HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
    server_thread = Thread(target=server_instance.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # 3. 브라우저 인증 페이지 열기
    auth_params = {
        "client_id": rest_api_key,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message"
    }
    login_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print(f"\n🌐 브라우저를 열어 카카오 로그인을 진행합니다...")
    webbrowser.open(login_url)
    print("💡 브라우저에서 '동의하고 계속하기'를 클릭해주세요. (대기 중...)")

    # 4. 코드 수신 대기
    import time
    for _ in range(60):
        if auth_code:
            break
        time.sleep(1)

    server_instance.shutdown()

    if not auth_code:
        print("❌ 인증 대기 시간이 초과되었거나 취소되었습니다.")
        return

    # 5. 토큰 발급
    try:
        token_res = exchange_code_for_tokens(rest_api_key, auth_code)
        refresh_token = token_res.get("refresh_token")

        print("\n" + "=" * 65)
        print("🎉 축하합니다! 카카오 인증이 성공적으로 완료되었습니다.")
        print("=" * 65)
        print(f"• KAKAO_REST_API_KEY: {rest_api_key}")
        print(f"• KAKAO_REFRESH_TOKEN: {refresh_token}")
        print("=" * 65)

        # .env 자동 업데이트
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        # 기존 키 제거 후 추가
        new_lines = [l for l in lines if not l.startswith("KAKAO_REST_API_KEY") and not l.startswith("KAKAO_REFRESH_TOKEN")]
        new_lines.append(f"\nKAKAO_REST_API_KEY={rest_api_key}\n")
        new_lines.append(f"KAKAO_REFRESH_TOKEN={refresh_token}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print("\n✅ 로컬 .env 파일에 카카오 키가 자동으로 저장되었습니다!")
        print("\n💡 [GitHub Actions 24시간 자동화 사용 시]")
        print("GitHub 저장소 Settings -> Secrets -> Actions에 아래 2개를 추가하세요:")
        print(f"1. KAKAO_REST_API_KEY  : {rest_api_key}")
        print(f"2. KAKAO_REFRESH_TOKEN : {refresh_token}")

    except Exception as e:
        print(f"❌ 토큰 발급 중 오류 발생: {e}")


if __name__ == "__main__":
    main()

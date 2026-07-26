# -*- coding: utf-8 -*-
"""
로컬 서버. site/ 폴더를 서빙하면서, 화면의 "새로고침" 버튼이 누르는
/api/refresh 엔드포인트를 처리합니다 (수집 → 차트조회 → 스케줄추정 → data.js 재생성).

실행: python local_server.py  (또는 refresh_and_open.bat 더블클릭)
종료: 이 창에서 Ctrl+C
"""
import http.server
import json
import os
import socketserver
import threading
import webbrowser

from collector import run_collection
from chart_tracker import refresh_all_charts
import build_site_data

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "site")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/refresh"):
            self._handle_refresh()
            return
        super().do_GET()

    def end_headers(self):
        # data.js는 브라우저가 캐싱하지 않고 항상 새로 받아오도록 강제
        if self.path.endswith("data.js"):
            self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _handle_refresh(self):
        print("\n[새로고침 요청] 수집을 시작합니다...")
        try:
            new_items = run_collection()
            _, chart_errors = refresh_all_charts()
            build_site_data.main()
            payload = {
                "status": "ok",
                "new_items": new_items,
                "chart_errors": [platform for platform, _ in chart_errors],
            }
        except Exception as e:
            payload = {"status": "error", "message": str(e)}
            print(f"[에러] 새로고침 중 문제 발생: {e}")

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # 정적 파일 요청 로그는 생략 (콘솔이 너무 지저분해지는 것 방지)
        if "/api/refresh" in (self.path or ""):
            print(f"[요청] {self.path}")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}/index.html"
        print("=" * 50)
        print(f"  RESCENE 트래커 서버 시작")
        print(f"  주소: {url}")
        print(f"  종료하려면 이 창에서 Ctrl+C")
        print("=" * 50)
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")


if __name__ == "__main__":
    main()

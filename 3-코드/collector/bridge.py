"""
bridge.py — 브라우저 확장 → 수집기 로컬 다리 (127.0.0.1:5077)

확장은 서버 주소도, 세션 id도, 로그인도 모른다. 그냥 이 다리에 던진다. 수집기가 받아서
  · tab 이벤트   → 자기 체인에 넣고(창 전환과 같은 순서로) 서버로 batch 전송
  · context 항목 → AI 질문·답 원문은 가려서 PC 에 저장 + 체인엔 해시만(ai_msg) — 모드 상관없이
                    그 밖의 맥락은 Learn 모드일 때만 옛 경로 (수집기가 거름)
이렇게 하면 체인의 순서를 정하는 곳이 수집기 하나뿐이라 "PC 체인 = 서버 재계산" 이 유지된다.

  GET  /status            → {session_id, work_id, recording:true, capture:{항목별 토글}}
  POST /event   {type:"tab", domain, title?, url?}            → 202
  POST /context {items:[{kind, text, meta}]}                  → 202 (기록 중이면 받음 · 거르는 건 수집기)
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 5077


def start(on_tab, on_context, status):
    """on_tab(ev) · on_context(items) 는 수집기 쪽 콜백. status() 는 현재 상태 dict 를 돌려준다."""

    class H(BaseHTTPRequestHandler):
        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def _json(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            self.send_response(204); self._cors(); self.end_headers()

        def do_GET(self):
            if self.path == "/status":
                return self._json(200, status())
            self._json(404, {"error": "not_found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"error": "bad_json"})
            if self.path == "/event":
                if body.get("type") != "tab":
                    return self._json(400, {"error": "only_tab_events"})
                on_tab(body); return self._json(202, {"ok": True})
            if self.path == "/context":
                if not status().get("recording"):
                    return self._json(409, {"error": "not_recording"})
                items = body.get("items") or []
                on_context(items); return self._json(202, {"accepted": len(items)})
            self._json(404, {"error": "not_found"})

        def log_message(self, *a):  # 콘솔은 수집기 출력만
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="bridge")
    t.start()
    return srv

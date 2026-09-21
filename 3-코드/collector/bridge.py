"""
bridge.py — 브라우저 확장 → 수집기 로컬 다리 (127.0.0.1:5077)

확장은 서버 주소도, 세션 id도, 로그인도 모른다. 그냥 이 다리에 던진다. 수집기가 받아서
  · tab 이벤트   → 자기 체인에 넣고(창 전환과 같은 순서로) 서버로 batch 전송
  · context 항목 → Learn 모드일 때만 서버 /sessions/{id}/context 로 전달 (체인에는 안 넣음)
이렇게 하면 체인의 순서를 정하는 곳이 수집기 하나뿐이라 "PC 체인 = 서버 재계산" 이 유지된다.

  GET  /status            → {session_id, mode, recording:true, learn_context:{...}}
  POST /event   {type:"tab", domain, title?, url?}            → 202
  POST /context {items:[{kind, text, meta}]}                  → 202 (learn 모드가 아니면 403)
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
                if status().get("mode") != "learn":
                    return self._json(403, {"error": "not_learn_mode"})
                items = body.get("items") or []
                on_context(items); return self._json(202, {"accepted": len(items)})
            self._json(404, {"error": "not_found"})

        def log_message(self, *a):  # 콘솔은 수집기 출력만
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="bridge")
    t.start()
    return srv

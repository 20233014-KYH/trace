"""
dev_receiver.py — 수집기 → Flask 전송 확인용 최소 서버 (app.py 나오기 전까지 임시)

받은 이벤트를 콘솔에 찍고 ../data/received.jsonl 에 그대로 쌓는다.
  python dev_receiver.py      # http://127.0.0.1:5000
"""
import json
import os

from flask import Flask, jsonify, request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "../data/received.jsonl"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)

app = Flask(__name__)


@app.post("/api/event")
def event():
    ev = request.get_json(force=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"← {ev.get('ts','')[11:19]} {ev.get('type'):13} {ev.get('app', ev.get('action', ''))}")
    return jsonify(ok=True, id=ev.get("id"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

"""
db.py — 저장소. SQLite (개발) / PostgreSQL (배포) 둘 다 같은 코드로 돈다.

★ 왜 SQLAlchemy 인가 ★
  SQL 문장을 직접 쓰지 않고 파이썬 객체로 다룬다. 배포할 때 주소만 바꾸면
  SQLite → PostgreSQL 로 옮겨간다. 초보가 SQL 오타로 하루 날리는 걸 막는다.

★ events 의 기본키가 (session_id, id) 인 이유 ★
  수집기가 붙이는 이벤트 id 는 evt_000001 처럼 '세션 안에서만' 고유하다.
  세션이 바뀌면 다시 evt_000001 부터 시작한다.
  id 하나만 기본키로 잡으면 두 번째 세션에서 충돌한다. (계약 확정본 A 검토 1곳)

★ batches 표가 따로 있는 이유 ★
  계약 3절 "이벤트 시각과 수신 시각 차이가 5분 넘으면 지연 수신으로 표시".
  배치마다 받은 시각을 남겨야 나중에 증명서에 그대로 쓸 수 있다.
"""
import os
import sys

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint, create_engine)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_URL = "sqlite:///" + os.path.join(HERE, "trace.db")


def _env_파일_읽기():
    """server/.env 의 KEY=VALUE 를 환경변수로 (이미 정해진 환경변수가 이긴다).
    DB 비밀번호가 든 주소를 코드나 저장소에 쓰지 않기 위해서다. .env 는 .gitignore 에 걸려 있다."""
    p = os.path.join(HERE, ".env")
    if not os.path.exists(p):
        return
    for 줄 in open(p, encoding="utf-8"):
        줄 = 줄.strip()
        if 줄 and not 줄.startswith("#") and "=" in 줄:
            키, 값 = 줄.split("=", 1)
            값 = 값.strip().strip('"').strip("'")
            if 값:                                   # 빈 칸(TRACE_DB_URL=)이면 없는 것으로 친다
                os.environ.setdefault(키.strip(), 값)


_env_파일_읽기()
DB_URL = os.environ.get("TRACE_DB_URL") or DEFAULT_URL     # 비어 있어도 기본(SQLite)으로

# Supabase 가 주는 주소(postgresql:// 또는 postgres://) → SQLAlchemy 가 psycopg 로 붙게
for 앞 in ("postgres://", "postgresql://"):
    if DB_URL.startswith(앞):
        DB_URL = "postgresql+psycopg://" + DB_URL[len(앞):]
if "[YOUR-PASSWORD]" in DB_URL:
    sys.exit("server/.env 의 주소에 [YOUR-PASSWORD] 가 그대로 있습니다 — 대괄호까지 지우고 진짜 DB 비밀번호로 바꿔 주세요.")

# ★ 화면·로그에는 이것만 찍는다. Supabase 주소엔 DB 비밀번호가 들어 있다
DB_URL_SAFE = make_url(DB_URL).render_as_string(hide_password=True)
인터넷DB = DB_URL.startswith("postgresql")

engine = create_engine(DB_URL, future=True,
                       pool_pre_ping=인터넷DB,          # 인터넷 DB 는 쉬는 동안 연결이 끊길 수 있다 → 쓰기 전에 확인
                       connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime)


class Token(Base):
    """로그인 토큰. JWT 대신 무작위 문자열을 DB 에 둔다.

    ★ 왜 JWT 가 아닌가 ★
      JWT 는 서버가 들고 있지 않아서 '로그아웃·강제 만료'를 할 수 없다.
      학생 기록을 다루는 서비스라 "이 기기 연결 끊기"가 되어야 한다.
      표 하나면 그게 되고, 초보가 봐도 무슨 일이 일어나는지 보인다.
    """
    __tablename__ = "tokens"
    token = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"))
    device = Column(String(100))
    created_at = Column(DateTime)
    last_used_at = Column(DateTime)


class Work(Base):
    """하나의 과제. 9/30 개정: 모드·과제 유형 없음. ai_scope = 교수가 허용한 범위 메모(선택, 판단에 안 씀)."""
    __tablename__ = "works"
    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"))
    title = Column(String(255))
    ai_scope = Column(Text)
    created_at = Column(DateTime)
    sessions = relationship("Sess", back_populates="work")


class Device(Base):
    __tablename__ = "devices"
    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"))
    name = Column(String(100))
    os = Column(String(16))
    collector_version = Column(String(32))


class Sess(Base):
    """수집기가 켜져 있던 한 번. id 는 수집기가 만든 UUID (오프라인에서도 시작해야 하므로)."""
    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True)
    work_id = Column(String(64), ForeignKey("works.id"))
    device_id = Column(String(64))
    mode = Column(String(16))              # 쓰지 않음 — 9/28 이전 기록을 읽기 위해 칸만 남김 (계약 v2.1)
    started_at = Column(String(40))
    ended_at = Column(String(40))
    sealed_at = Column(String(40))
    root = Column(String(64))
    head = Column(String(64))              # 서버가 재계산한 지금까지의 체인 끝
    chain_len = Column(Integer, default=0)
    integrity_ok = Column(Boolean, default=True)
    verified = Column(Boolean)
    last_heartbeat_at = Column(String(40))
    anchor_status = Column(String(16), default="none")
    anchor_submitted_at = Column(String(40))
    work = relationship("Work", back_populates="sessions")


class Event(Base):
    __tablename__ = "events"
    session_id = Column(String(64), ForeignKey("sessions.id"), primary_key=True)
    id = Column(String(64), primary_key=True)          # ★ 복합키. 세션 안에서만 고유하다
    seq = Column(Integer)                              # 받은 순서
    ts = Column(String(40))
    type = Column(String(32))
    payload = Column(JSON)                             # 이벤트 한 줄 원본 그대로
    h = Column(String(64))                             # 수집기가 붙여 보낸 해시 (참고용)
    server_h = Column(String(64))                      # 서버가 재계산한 해시
    received_at = Column(String(40))


class Batch(Base):
    """배치 하나가 언제 도착했나. 지연 수신 판정에 쓴다."""
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id"))
    chain_head = Column(String(64))
    chain_len = Column(Integer)
    n = Column(Integer)
    late = Column(Integer, default=0)
    verified = Column(Boolean)
    received_at = Column(String(40))


class Context(Base):
    """AI 대화 기록 (옛 Learn 맥락). 9/28 부터 모든 세션에서 받는다 (계약 4절)."""
    __tablename__ = "contexts"
    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), ForeignKey("sessions.id"))
    ts = Column(String(40))
    source = Column(String(16))
    kind = Column(String(32))
    text = Column(Text)
    meta = Column(JSON)


def init():
    Base.metadata.create_all(engine)
    _칸_추가()
    if 인터넷DB:
        _행_보안_켜기()
    return engine


def _행_보안_켜기():
    """★ Supabase 는 public 스키마의 표를 '데이터 API'로 인터넷에 내놓는다 ★

    SQL 로 만든 표는 행 보안(RLS)이 꺼진 채라, 프로젝트의 공개 키(anon key)만 있으면 표를 읽을 수 있다.
    → 표마다 RLS 를 켜고 정책은 하나도 안 만든다 = 데이터 API 로는 아무것도 못 읽음.
    우리 서버는 표의 주인(postgres)으로 붙으므로 RLS 와 상관없이 그대로 읽고 쓴다.
    여러 번 켜도 안전하다.
    """
    from sqlalchemy import text
    with engine.begin() as 연결:
        for 표 in Base.metadata.sorted_tables:
            연결.execute(text(f'ALTER TABLE "{표.name}" ENABLE ROW LEVEL SECURITY'))


def _칸_추가():
    """★ 마이그레이션 — 이미 있는 DB 파일에 새 칸을 넣는다 ★

    create_all 은 '없는 표'만 만든다. 이미 있는 표에 칸이 늘어난 것은 모른다.
    그래서 9/23 에 만든 trace.db 의 works 표에는 ai_scope 칸이 없고,
    그대로 켜면 "no such column: works.ai_scope" 로 서버가 죽는다.
    → 칸이 없으면 ALTER TABLE 로 붙인다. 이미 있으면 아무것도 안 한다 (여러 번 켜도 안전).
    """
    from sqlalchemy import inspect, text
    있는칸 = {c["name"] for c in inspect(engine).get_columns("works")}
    if "ai_scope" not in 있는칸:
        with engine.begin() as 연결:
            연결.execute(text("ALTER TABLE works ADD COLUMN ai_scope TEXT"))
        print("  DB: works 표에 ai_scope 칸을 붙였습니다 (한 번만)")


if __name__ == "__main__":
    init()
    print("만들었습니다:", DB_URL_SAFE)
    for t in Base.metadata.sorted_tables:
        print(f"  {t.name:<12} {', '.join(c.name for c in t.columns)}")

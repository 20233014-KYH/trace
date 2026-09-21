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

from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_URL = "sqlite:///" + os.path.join(HERE, "trace.db")
DB_URL = os.environ.get("TRACE_DB_URL", DEFAULT_URL)

engine = create_engine(DB_URL, future=True,
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


class Work(Base):
    """하나의 과제·작업. 한 Work = 한 모드 (learn 또는 proof)."""
    __tablename__ = "works"
    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"))
    title = Column(String(255))
    mode = Column(String(16))
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
    mode = Column(String(16))
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
    """Learn 맥락. Proof 세션에는 저장하지 않는다 (계약 5절)."""
    __tablename__ = "contexts"
    id = Column(String(64), primary_key=True)
    session_id = Column(String(64), ForeignKey("sessions.id"))
    ts = Column(String(40))
    source = Column(String(16))
    kind = Column(String(32))
    text = Column(Text)
    meta = Column(JSON)


class Report(Base):
    __tablename__ = "reports"
    session_id = Column(String(64), ForeignKey("sessions.id"), primary_key=True)
    body = Column(JSON)
    generated_at = Column(String(40))
    provider = Column(String(32))
    runs = Column(Integer, default=0)
    chat_turns = Column(Integer, default=0)


def init():
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    init()
    print("만들었습니다:", DB_URL)
    for t in Base.metadata.sorted_tables:
        print(f"  {t.name:<12} {', '.join(c.name for c in t.columns)}")

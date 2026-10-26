"""SQLAlchemy 엔진/세션 - TiDB Cloud (MySQL 8.x 호환, TLS)."""
import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    connect_args = {"charset": "utf8mb4"}
    if settings.db_ssl:
        connect_args["ssl"] = {"ca": certifi.where()}
    # TiDB 유휴 연결 끊김 대응 (pool_pre_ping, pool_recycle)
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=5)


engine = make_engine(settings.require_database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (테이블 등록)

    Base.metadata.create_all(bind=engine)

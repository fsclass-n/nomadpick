"""NomadPick 데이터 모델 (10개 테이블)."""
from datetime import date, datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGBLOB, LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import now_kst

# TiDB(MySQL 8.x) 타입
BigId = BigInteger
LongBlob = LONGBLOB
LongText = LONGTEXT


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(10), default="USER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)

    preference: Mapped["UserPreference | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(BigId, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    regions: Mapped[list] = mapped_column(JSON, default=list)
    budget_min: Mapped[int | None] = mapped_column(Integer)
    budget_max: Mapped[int | None] = mapped_column(Integer)
    depart_months: Mapped[list] = mapped_column(JSON, default=list)
    nights_min: Mapped[int | None] = mapped_column(SmallInteger)
    nights_max: Mapped[int | None] = mapped_column(SmallInteger)
    theme: Mapped[str | None] = mapped_column(String(20))
    companion: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst, onupdate=now_kst)

    user: Mapped[User] = relationship(back_populates="preference")


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(200))
    robots_checked_at: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TravelProduct(Base):
    __tablename__ = "travel_products"
    __table_args__ = (
        UniqueConstraint("agency_id", "product_code", "depart_date", name="uq_product"),
        Index("ix_product_region_depart", "region", "depart_date"),
    )
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(50))
    theme: Mapped[str | None] = mapped_column(String(20))
    depart_date: Mapped[date] = mapped_column(Date, nullable=False)
    depart_end: Mapped[date | None] = mapped_column(Date)  # 출발 기간·날짜 목록의 마지막 출발일
    nights: Mapped[int | None] = mapped_column(SmallInteger)
    days: Mapped[int | None] = mapped_column(SmallInteger)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[int | None] = mapped_column(Integer)
    discount_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    seats_left: Mapped[int | None] = mapped_column(Integer)
    airline: Mapped[str | None] = mapped_column(String(50))
    image_url: Mapped[str | None] = mapped_column(String(500))
    detail_url: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(10), default="live")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    agency: Mapped[Agency] = relationship()


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (Index("ix_snapshot_product_time", "product_id", "collected_at"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("travel_products.id", ondelete="CASCADE"), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    seats_left: Mapped[int | None] = mapped_column(Integer)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Airport(Base):
    """국토교통부 국내항공운항정보 - 공항 목록."""
    __tablename__ = "airports"
    airport_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    airport_nm: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst, onupdate=now_kst)


class FlightSchedule(Base):
    """국토교통부 국내항공운항정보 - 항공편 운항 정보."""
    __tablename__ = "flight_schedules"
    __table_args__ = (
        UniqueConstraint("flight_date", "flight_no", "dep_airport_id", "dep_time", name="uq_flight"),
        Index("ix_flight_route_date", "dep_airport_id", "arr_airport_id", "flight_date"),
    )
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    dep_airport_id: Mapped[str] = mapped_column(String(10), nullable=False)
    arr_airport_id: Mapped[str] = mapped_column(String(10), nullable=False)
    dep_airport_nm: Mapped[str | None] = mapped_column(String(50))
    arr_airport_nm: Mapped[str | None] = mapped_column(String(50))
    airline_nm: Mapped[str | None] = mapped_column(String(50))
    flight_no: Mapped[str] = mapped_column(String(20), nullable=False)
    dep_time: Mapped[str] = mapped_column(String(12), nullable=False)
    arr_time: Mapped[str | None] = mapped_column(String(12))
    economy_charge: Mapped[int | None] = mapped_column(Integer)
    prestige_charge: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10), default="live")
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_favorite"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("travel_products.id", ondelete="CASCADE"), nullable=False)
    saved_price: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)

    product: Mapped[TravelProduct] = relationship()


class RpaJobLog(Base):
    __tablename__ = "rpa_job_logs"
    __table_args__ = (Index("ix_job_started", "started_at"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(30), nullable=False)
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str | None] = mapped_column(String(10))
    collected: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    agency: Mapped[Agency | None] = relationship()


class ExcelReport(Base):
    __tablename__ = "excel_reports"
    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_blob: Mapped[bytes] = mapped_column(LongBlob, nullable=False)
    chart_html: Mapped[str | None] = mapped_column(LongText)
    summary: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)

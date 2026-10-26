"""상품 조회·직렬화 공통 로직."""
from datetime import timedelta

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..constants import CITY_AIRPORT, HOME_AIRPORT_ID
from ..models import FlightSchedule, PriceSnapshot, TravelProduct
from ..utils import today_kst


def serialize(p: TravelProduct) -> dict:
    return {
        "id": p.id,
        "product_code": p.product_code,
        "title": p.title,
        "agency": p.agency.name if p.agency else None,
        "agency_code": p.agency.code if p.agency else None,
        "region": p.region,
        "country_code": p.country_code,
        "city": p.city,
        "theme": p.theme,
        "depart_date": p.depart_date.isoformat(),
        "depart_end": p.depart_end.isoformat() if p.depart_end else None,
        "nights": p.nights,
        "days": p.days,
        "price": p.price,
        "original_price": p.original_price,
        "discount_rate": float(p.discount_rate or 0),
        "seats_left": p.seats_left,
        "airline": p.airline,
        "image_url": p.image_url,
        "detail_url": p.detail_url,
        "source": p.source,
        "is_domestic": p.region == "국내",
        "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
    }


def last_depart_date():
    """출발 기간 상품은 마지막 출발일, 단일 출발 상품은 출발일."""
    return func.coalesce(TravelProduct.depart_end, TravelProduct.depart_date)


def active_products_query():
    return (select(TravelProduct).options(joinedload(TravelProduct.agency))
            .where(TravelProduct.is_active.is_(True), last_depart_date() >= today_kst()))


def next_departure(p: TravelProduct) -> date:
    """출발 기간 상품의 다음 출발 가능일 (오늘 이후 첫날)."""
    return max(p.depart_date, today_kst()) if p.depart_end else p.depart_date


def last_collected_at(db: Session):
    return db.scalar(select(func.max(TravelProduct.last_seen_at)).where(TravelProduct.is_active.is_(True)))


def price_history(db: Session, product_id: int, days: int = 30) -> list[dict]:
    since = today_kst() - timedelta(days=days)
    rows = db.scalars(select(PriceSnapshot).where(PriceSnapshot.product_id == product_id, PriceSnapshot.collected_at >= since)
                      .order_by(PriceSnapshot.collected_at)).all()
    return [{"collected_at": r.collected_at.isoformat(), "price": r.price, "seats_left": r.seats_left} for r in rows]


def previous_price(db: Session, product: TravelProduct) -> int | None:
    """직전 수집 시점의 가격."""
    rows = db.scalars(select(PriceSnapshot.price).where(PriceSnapshot.product_id == product.id)
                      .order_by(PriceSnapshot.collected_at.desc()).limit(2)).all()
    return rows[1] if len(rows) > 1 else None


def flights_for(db: Session, product: TravelProduct) -> list[dict]:
    """국내 상품 - 출발일 김포 → 목적지 국내선 운항 정보(국토교통부)."""
    arr = CITY_AIRPORT.get(product.city or "")
    if product.region != "국내" or not arr:
        return []
    rows = db.scalars(select(FlightSchedule).where(
        FlightSchedule.dep_airport_id == HOME_AIRPORT_ID, FlightSchedule.arr_airport_id == arr,
        FlightSchedule.flight_date == next_departure(product)).order_by(FlightSchedule.dep_time)).all()
    return [{
        "flight_date": f.flight_date.isoformat(), "airline_nm": f.airline_nm, "flight_no": f.flight_no, "dep_airport_nm": f.dep_airport_nm,
        "arr_airport_nm": f.arr_airport_nm, "dep_time": f.dep_time, "arr_time": f.arr_time,
        "economy_charge": f.economy_charge, "prestige_charge": f.prestige_charge, "source": f.source,
    } for f in rows]

"""RPA 수집 결과 적재 - 상품 upsert + 가격 스냅샷, 항공편·공항, 로그, 리포트.

API(/rpa/*) 와 서버 내장 스케줄러(direct sink) 가 같은 함수를 사용한다.
"""
from datetime import date, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..models import Agency, Airport, ExcelReport, FlightSchedule, PriceSnapshot, RpaJobLog, TravelProduct
from ..utils import now_kst, to_kst_naive, today_kst
from .products import last_depart_date

PRODUCT_FIELDS = ("title", "region", "country_code", "city", "theme", "depart_end", "nights", "days", "price",
                  "original_price", "seats_left", "airline", "image_url", "detail_url")


def get_agency(db: Session, code: str | None) -> Agency | None:
    return db.scalar(select(Agency).where(Agency.code == code)) if code else None


def discount_rate(price: int, original: int | None) -> float:
    return round((original - price) / original * 100, 2) if original and original > price else 0.0


def upsert_products(db: Session, agency_code: str, collected_at: datetime, source: str, items: list[dict]) -> dict:
    agency = get_agency(db, agency_code)
    if agency is None:
        raise ValueError(f"알 수 없는 여행사 코드: {agency_code}")
    collected_at = to_kst_naive(collected_at)
    codes = {i["product_code"] for i in items}
    rows = db.scalars(select(TravelProduct).where(TravelProduct.agency_id == agency.id,
                                                  TravelProduct.product_code.in_(codes))).all() if codes else []
    existing = {(p.product_code, p.depart_date): p for p in rows}
    latest = {p.product_code: p for p in sorted(rows, key=lambda p: p.last_seen_at or datetime.min)}

    inserted = updated = 0
    touched: list[TravelProduct] = []
    seen: set[tuple] = set()
    for item in items:
        key = (item["product_code"], item["depart_date"])
        if key in seen:  # 같은 수집 내 중복 노출(여러 기획전) 제거
            continue
        seen.add(key)
        product = existing.get(key)
        if product is None and item.get("depart_anytime") and item["product_code"] in latest:
            # 상시 출발 상품은 출발일이 수집일로 매일 바뀌므로 같은 상품 행을 이어 쓴다(가격 이력 유지)
            product = latest.pop(item["product_code"])
            product.depart_date = item["depart_date"]
        if product is None:
            product = TravelProduct(agency_id=agency.id, product_code=item["product_code"],
                                    depart_date=item["depart_date"], first_seen_at=collected_at)
            db.add(product)
            inserted += 1
        else:
            updated += 1
        for f in PRODUCT_FIELDS:
            setattr(product, f, item.get(f))
        product.discount_rate = discount_rate(item["price"], item.get("original_price"))
        product.source = source
        product.last_seen_at = collected_at
        product.is_active = True
        touched.append(product)
    db.flush()

    for p in touched:
        db.add(PriceSnapshot(product_id=p.id, price=p.price, seats_left=p.seats_left, collected_at=collected_at))

    deactivated = 0
    if touched:
        deactivated = db.execute(
            update(TravelProduct)
            .where(TravelProduct.agency_id == agency.id, TravelProduct.is_active.is_(True),
                   TravelProduct.last_seen_at < collected_at)
            .values(is_active=False)
        ).rowcount
    db.execute(update(TravelProduct).where(last_depart_date() < today_kst(), TravelProduct.is_active.is_(True))
               .values(is_active=False))
    db.commit()
    return {"inserted": inserted, "updated": updated, "snapshots": len(touched), "deactivated": deactivated}


def upsert_flights(db: Session, items: list[dict], source: str = "live") -> dict:
    inserted = updated = 0
    if source == "live":  # 실데이터가 들어온 노선·날짜의 sample 운항정보는 제거
        for dep, arr, day in {(i["dep_airport_id"], i["arr_airport_id"], i["flight_date"]) for i in items}:
            db.execute(delete(FlightSchedule).where(
                FlightSchedule.dep_airport_id == dep, FlightSchedule.arr_airport_id == arr,
                FlightSchedule.flight_date == day, FlightSchedule.source == "sample"))
    for it in items:
        row = db.scalar(select(FlightSchedule).where(
            FlightSchedule.flight_date == it["flight_date"], FlightSchedule.flight_no == it["flight_no"],
            FlightSchedule.dep_airport_id == it["dep_airport_id"], FlightSchedule.dep_time == it["dep_time"]))
        if row is None:
            row = FlightSchedule(**it, source=source, collected_at=now_kst())
            db.add(row)
            inserted += 1
        else:
            for k, v in it.items():
                setattr(row, k, v)
            row.source, row.collected_at = source, now_kst()
            updated += 1
    db.commit()
    return {"inserted": inserted, "updated": updated}


def upsert_airports(db: Session, items: list[dict]) -> dict:
    count = 0
    for it in items:
        row = db.get(Airport, it["airport_id"])
        if row is None:
            db.add(Airport(**it))
        else:
            row.airport_nm = it["airport_nm"]
            row.city = it.get("city") or row.city
        count += 1
    db.commit()
    return {"upserted": count}


def add_log(db: Session, data: dict) -> RpaJobLog:
    agency = get_agency(db, data.pop("agency_code", None))
    data["started_at"] = to_kst_naive(data["started_at"])
    if data.get("ended_at"):
        data["ended_at"] = to_kst_naive(data["ended_at"])
    if data.get("message"):
        data["message"] = data["message"][:500]
    log = RpaJobLog(**data, agency_id=agency.id if agency else None)
    db.add(log)
    db.commit()
    return log


def save_report(db: Session, report_date: date, file_name: str, blob: bytes, chart_html: str | None, summary: dict | None) -> ExcelReport:
    row = db.scalar(select(ExcelReport).where(ExcelReport.report_date == report_date))
    if row is None:
        row = ExcelReport(report_date=report_date, file_name=file_name, file_blob=blob)
        db.add(row)
    row.file_name, row.file_blob, row.chart_html, row.summary = file_name, blob, chart_html, summary
    db.commit()
    return row

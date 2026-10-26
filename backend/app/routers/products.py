from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..constants import AGENCIES, COMPANIONS, REGIONS, THEMES
from ..database import get_db
from ..models import Agency, Favorite, TravelProduct, User
from ..security import api_error, get_optional_user
from ..services.products import (active_products_query, flights_for, last_collected_at, last_depart_date,
                                 previous_price, price_history, serialize)

router = APIRouter(tags=["상품"])

SORTS = {
    "discount": (TravelProduct.discount_rate.desc(), TravelProduct.price),
    "price": (TravelProduct.price, TravelProduct.discount_rate.desc()),
    "depart": (TravelProduct.depart_date, TravelProduct.price),
}


@router.get("/meta", summary="필터 코드값·서비스 통계")
def meta(db: Session = Depends(get_db)):
    q = active_products_query().subquery()
    total = db.scalar(select(func.count()).select_from(q)) or 0
    by_agency = dict(db.execute(select(q.c.agency_id, func.count()).group_by(q.c.agency_id)).all())
    collected = last_collected_at(db)
    return {
        "regions": REGIONS, "themes": THEMES, "companions": COMPANIONS,
        "agencies": [{**a, "count": by_agency.get(a["id"], 0)} for a in AGENCIES],
        "total": total, "collected_at": collected.isoformat() if collected else None,
    }


@router.get("/products", summary="특가 목록(필터·정렬·페이지)")
def list_products(
    region: str | None = Query(None, description="지역(쉼표 구분 복수)"),
    price_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, ge=0),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="출발월 YYYY-MM"),
    agency: str | None = Query(None, description="여행사 ID 또는 코드"),
    theme: str | None = None,
    q: str | None = Query(None, max_length=50, description="상품명·도시 검색"),
    sort: str = Query("discount", pattern="^(discount|price|depart)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = active_products_query()
    if region:
        stmt = stmt.where(TravelProduct.region.in_([r.strip() for r in region.split(",") if r.strip()]))
    if price_min is not None:
        stmt = stmt.where(TravelProduct.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(TravelProduct.price <= price_max)
    if month:
        y, m = map(int, month.split("-"))
        start = date(y, m, 1)
        end = date(y + (m == 12), m % 12 + 1, 1)
        stmt = stmt.where(TravelProduct.depart_date < end, last_depart_date() >= start)  # 출발 기간이 해당 월과 겹침
    if agency:
        stmt = stmt.join(Agency).where(Agency.id == int(agency)) if agency.isdigit() else stmt.join(Agency).where(Agency.code == agency)
    if theme:
        stmt = stmt.where(TravelProduct.theme == theme)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(TravelProduct.title.like(like), TravelProduct.city.like(like)))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.order_by(*SORTS[sort]).offset((page - 1) * size).limit(size)).unique().all()
    collected = last_collected_at(db)
    return {"total": total, "page": page, "size": size,
            "collected_at": collected.isoformat() if collected else None,
            "items": [serialize(p) for p in rows]}


def _get_product(db: Session, product_id: int) -> TravelProduct:
    product = db.get(TravelProduct, product_id)
    if product is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.")
    return product


@router.get("/products/{product_id}", summary="상품 상세(국내선 항공편 포함)")
def product_detail(product_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    product = _get_product(db, product_id)
    favorite = None
    if user:
        favorite = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product.id))
    return {**serialize(product), "is_active": product.is_active,
            "previous_price": previous_price(db, product),
            "is_favorite": favorite is not None,
            "saved_price": favorite.saved_price if favorite else None,
            "flights": flights_for(db, product)}


@router.get("/products/{product_id}/prices", summary="가격 이력(기본 30일)")
def product_prices(product_id: int, days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    _get_product(db, product_id)
    return {"product_id": product_id, "days": days, "items": price_history(db, product_id, days)}

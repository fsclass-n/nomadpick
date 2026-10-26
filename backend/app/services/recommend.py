"""맞춤 추천 - scikit-learn 코사인 유사도 + 가점.

추천 점수 = 선호 유사도 × 60 + 할인율 가점(최대 20) + 출발월 일치 10 + 예산 범위 내 10
제외 조건: 잔여석 0, 출발일 경과, 비활성 상품
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from ..constants import REGIONS, THEMES
from ..models import TravelProduct, UserPreference
from .products import active_products_query, serialize

PRICE_CAP = 3_000_000
NIGHTS_CAP = 10
REGION_WEIGHT = 1.5


def _product_matrix(products: list[TravelProduct]) -> np.ndarray:
    rows = []
    for p in products:
        region = [REGION_WEIGHT if p.region == r else 0.0 for r in REGIONS]
        theme = [1.0 if p.theme == t else 0.0 for t in THEMES]
        rows.append(region + theme + [min(p.price, PRICE_CAP) / PRICE_CAP, min(p.nights or 0, NIGHTS_CAP) / NIGHTS_CAP])
    return np.array(rows, dtype=float)


def _user_vector(pref: UserPreference) -> np.ndarray:
    region = [REGION_WEIGHT if r in (pref.regions or []) else 0.0 for r in REGIONS]
    theme = [1.0 if pref.theme == t else 0.0 for t in THEMES]
    lo, hi = pref.budget_min or 0, pref.budget_max or PRICE_CAP
    n_lo, n_hi = pref.nights_min or 0, pref.nights_max or NIGHTS_CAP
    return np.array([region + theme + [min((lo + hi) / 2, PRICE_CAP) / PRICE_CAP, min((n_lo + n_hi) / 2, NIGHTS_CAP) / NIGHTS_CAP]])


def depart_months(p: TravelProduct) -> set[str]:
    """출발 가능 월(YYYY-MM) 집합 - 출발 기간 상품은 기간 내 모든 월."""
    start, end = p.depart_date, p.depart_end or p.depart_date
    months, y, m = set(), start.year, start.month
    while (y, m) <= (end.year, end.month) and len(months) < 24:
        months.add(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def _has_preference(pref: UserPreference | None) -> bool:
    return bool(pref and (pref.regions or pref.theme or pref.budget_max or pref.depart_months))


def recommend(db: Session, pref: UserPreference | None, limit: int = 10) -> list[dict]:
    products = [p for p in db.scalars(active_products_query()).unique().all() if p.seats_left != 0]
    if not products:
        return []

    if not _has_preference(pref):
        products.sort(key=lambda p: float(p.discount_rate or 0), reverse=True)
        return [{**serialize(p), "product_id": p.id, "score": round(float(p.discount_rate or 0), 1),
                 "reasons": [f"할인율 {float(p.discount_rate or 0):.0f}%", "선호 미설정 - 할인율 순 추천"]} for p in products[:limit]]

    sims = cosine_similarity(_user_vector(pref), _product_matrix(products))[0]
    months = set(pref.depart_months or [])
    results = []
    for p, sim in zip(products, sims):
        discount = float(p.discount_rate or 0)
        month_ok = bool(months & depart_months(p))
        budget_ok = (pref.budget_min or 0) <= p.price <= (pref.budget_max or PRICE_CAP * 10)
        score = sim * 60 + min(discount, 40) / 40 * 20 + (10 if month_ok else 0) + (10 if budget_ok else 0)

        reasons = []
        if p.region in (pref.regions or []):
            reasons.append(f"선호 지역({p.region}) 일치")
        if pref.theme and p.theme == pref.theme:
            reasons.append(f"테마({p.theme}) 일치")
        if budget_ok and pref.budget_max:
            reasons.append(f"예산 {pref.budget_max // 10000:,}만 원 이내")
        if month_ok:
            reasons.append(f"{min(months & depart_months(p))[5:].lstrip('0')}월 출발")
        if pref.nights_min is not None and pref.nights_max is not None and p.nights is not None \
                and pref.nights_min <= p.nights <= pref.nights_max:
            reasons.append(f"{p.nights}박 {p.days}일 일정")
        if discount >= 20:
            reasons.append(f"할인율 {discount:.0f}%")
        results.append({**serialize(p), "product_id": p.id, "score": round(float(score), 1), "reasons": reasons})

    results.sort(key=lambda r: (r["score"], r["discount_rate"]), reverse=True)
    return _diversify(results, limit)


def _diversify(results: list[dict], limit: int, per_city: int = 2) -> list[dict]:
    """같은 상품(출발일만 다른 경우)은 1건, 같은 도시는 최대 2건으로 제한하여 다양성 확보."""
    picked, products, cities = [], set(), {}
    for r in results:
        key = (r["agency_code"], r["product_code"])
        if key in products or cities.get(r["city"], 0) >= per_city:
            continue
        products.add(key)
        cities[r["city"]] = cities.get(r["city"], 0) + 1
        picked.append(r)
        if len(picked) == limit:
            break
    return picked

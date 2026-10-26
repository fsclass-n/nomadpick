"""내장 샘플 특가 페이지 생성기 (auto 모드 대체 수집 · 테스트용).

Playwright live 수집이 실패(사이트 장애·차단·브라우저 미설치)하면 이 모듈이 여행사 실제 페이지와 같은 마크업
(하나투어 div.card-wrap, 노랑풍선 ul.list_thum, 모두투어 __NEXT_DATA__ JSON)으로 HTML 을 생성하고,
live 와 동일한 파서·정제·적재 파이프라인으로 처리한다. 생성된 데이터는 source='sample' 로 구분 저장된다.
"""
import hashlib
import json
import random
from datetime import date, datetime, timedelta
from html import escape

from ..catalog import AGENCY_CATALOG, CATALOG

WEEKDAYS = "월화수목금토일"
AGENCY_PREFIX = {"hanatour": "HT", "modetour": "MT", "ybtour": "YB"}
AGENCY_PRICE_FACTOR = {"hanatour": 1.0, "modetour": 0.97, "ybtour": 0.95}
CATALOG_BY_KEY = {row[0]: row for row in CATALOG}


def seeded_rng(*parts) -> random.Random:
    seed = int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def _depart_dates(agency: str, key: str, weekday: int, today: date, count: int = 3) -> list[date]:
    """출발 요일 기준 절대 날짜(매일 바뀌지 않음) 중 여행사·상품별로 격주/3주 간격 선택."""
    start = today + timedelta(days=7)
    first = start + timedelta(days=(weekday - start.weekday()) % 7)
    step = seeded_rng(agency, key, "step").choice([1, 2, 3])
    dates, d = [], first
    while len(dates) < count and d <= today + timedelta(days=150):
        if d.isocalendar()[1] % step == 0:
            dates.append(d)
        d += timedelta(days=7)
    return dates


def _won(v: int) -> int:
    return max(int(round(v / 10000) * 10000) - 1000, 9000)


def build_items(agency: str, at: datetime) -> list[dict]:
    """여행사·시각별 샘플 특가(정형 데이터). 가격은 6시간 단위로 변동, 잔여석은 출발이 가까울수록 감소."""
    items = []
    for idx, key in enumerate(AGENCY_CATALOG[agency], start=1):
        _, city, title, nights, days, base, (dmin, dmax), _theme, airline, weekday = CATALOG_BY_KEY[key]
        for dep in _depart_dates(agency, key, weekday, at.date()):
            r0 = seeded_rng(agency, key, dep)
            original = int(round(base * AGENCY_PRICE_FACTOR[agency] * r0.uniform(0.95, 1.08), -4))
            drift = seeded_rng(agency, key, dep, at.date(), at.hour // 6).uniform(-0.03, 0.03)
            discount = min(max(r0.uniform(dmin, dmax) / 100 + drift, 0.03), 0.6)
            price = _won(original * (1 - discount))
            days_left = (dep - at.date()).days
            seats = max(0, int(r0.randint(4, 24) * min(1.0, days_left / 60)) - (1 if r0.random() < 0.05 else 0))
            if r0.random() < 0.04:
                seats = 0
            label = r0.choice(["[특가]", "[단독특가]", "[얼리버드]", "[마감임박]", ""])
            items.append({
                "code": f"{AGENCY_PREFIX[agency]}-{key}{idx:02d}",
                "title": f"{label} {title} {nights}박{days}일".strip(),
                "depart": dep, "nights": nights, "days": days, "price": price, "original": original,
                "seats": seats, "airline": airline,
            })
    return items


def _hanatour(items: list[dict]) -> str:
    cards = []
    for i, it in enumerate(items):
        d = it["depart"]
        cards.append(
            f'<div class="card-wrap" id="productInfo_{it["code"]}"><div class="section static"><div class="section">'
            f'<div class="label-group"><span class="label time pink">{d:%m.%d} 출발</span></div></div></div>'
            f'<div class="section"><div class="text-group"><p class="eps2">{escape(it["title"])}</p></div>'
            f'<div class="option-group"><span>인천</span><span>{it["days"]}일</span></div>'
            f'<div class="price-group"><span class="price"><strong>{it["price"]:,}</strong>원~</span></div></div></div>')
    return f'<html><body><div class="card-list-wrap medium">{"".join(cards)}</div></body></html>'


def _modetour(items: list[dict]) -> str:
    products = [{
        "masterCode": it["code"], "masterProductName": it["title"], "price": it["price"],
        "minDepartureDate": f'{it["depart"]:%Y-%m-%d}T00:00:00', "dates": [{"night": it["nights"], "days": it["days"]}],
        "depatureFrom": ["인천"], "productCodes": [{"marketingAirName": it["airline"]}],
    } for it in items]
    data = {"props": {"pageProps": {"dehydratedState": {"queries": [{"state": {"data": {"result": {"products": products}}}}]}}}}
    return ('<html><body><div id="__next"></div><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(data, ensure_ascii=False) + "</script></body></html>")


def _ybtour(items: list[dict]) -> str:
    rows = []
    for it in items:
        d = it["depart"]
        save = (it["original"] - it["price"]) // 10000
        rows.append(
            f'<li data-braze-temp-goods-cd="{it["code"]}"><a href="#yb"><div class="txt_content">'
            f'<p class="tit">{escape(it["title"])}<br/>ㄴ{save}만원 할인</p>'
            f'<p class="txt"><em>#긴급특가: {d.month}/{d.day}</em><br/>#{it["airline"]}</p>'
            f'<div class="box_price"><p class="price"><em>{it["original"]:,}</em>원~</p>'
            f'<p class="sale"><em>{it["price"]:,}</em>원~</p></div></div></a></li>')
    return f'<html><body><ul class="list_thum">{"".join(rows)}</ul></body></html>'


RENDERERS = {"hanatour": _hanatour, "modetour": _modetour, "ybtour": _ybtour}
SAMPLE_PAGE = {"hanatour": "https://www.hanatour.com/promotion/plan/PM006787B572",
               "modetour": "https://www.modetour.com/promotion/1542",
               "ybtour": "https://pkg.ybtour.co.kr/promotion/promotionDetail.yb?mstNo=20000028710"}


def render_page(agency: str, at: datetime) -> str:
    return RENDERERS[agency](build_items(agency, at))


def parse_sample(agency: str, at: datetime) -> list[dict]:
    """샘플 페이지를 live 와 같은 여행사 파서로 파싱한다."""
    from .agencies import COLLECTOR_BY_AGENCY

    return COLLECTOR_BY_AGENCY[agency]().parse(render_page(agency, at), SAMPLE_PAGE[agency])

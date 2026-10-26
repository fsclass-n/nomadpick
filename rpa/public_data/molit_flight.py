"""국토교통부_(TAGO)_국내항공운항정보 API 연동.

- 공항 목록:     /GetArprtList
- 항공운항정보:  /GetFlightOpratInfoList (depAirportId, arrAirportId, depPlandTime=YYYYMMDD)
  (2026-03 개편: 서비스 경로가 DmstcFlightNvgInfoService → DmstcFlightNvgInfo, 오퍼레이션 첫 글자 대문자)
서비스 키(DATA_GO_KR_KEY)가 없거나 호출이 실패하면 sample 운항 정보로 대체(source='sample')한다.
"""
import logging
import time
from datetime import date
from urllib.parse import unquote

import requests

from backend.app.config import settings
from backend.app.constants import AIRPORTS

from ..collector.sample_site import seeded_rng

log = logging.getLogger(__name__)
BASE = "https://apis.data.go.kr/1613000/DmstcFlightNvgInfo"
AIRPORT_NM = {a["airport_id"]: a["airport_nm"] for a in AIRPORTS}


class PublicApiError(Exception):
    pass


def _items(payload: dict) -> list[dict]:
    resp = payload.get("response", {})
    code = resp.get("header", {}).get("resultCode")
    if code not in ("00", "0000", None):
        raise PublicApiError(f"{code} {resp.get('header', {}).get('resultMsg')}")
    items = (resp.get("body") or {}).get("items") or {}
    item = items.get("item", []) if isinstance(items, dict) else []
    return item if isinstance(item, list) else [item]


def _call(op: str, params: dict) -> list[dict]:
    key = unquote(settings.data_go_kr_key)  # Encoding 키를 넣어도 이중 인코딩되지 않도록
    query = {"serviceKey": key, "_type": "json", "numOfRows": 200, "pageNo": 1, **params}
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{op}", params=query, timeout=15)
            r.raise_for_status()
            if not r.text.strip().startswith("{"):
                raise PublicApiError(r.text[:200])
            return _items(r.json())
        except (requests.RequestException, ValueError) as e:
            if attempt == 3:
                raise PublicApiError(str(e)[:200]) from e
            time.sleep(2 ** (attempt + 1))
    return []


def _hhmm(v) -> str:
    s = str(v or "")
    return f"{s[8:10]}:{s[10:12]}" if len(s) >= 12 else s


def fetch_airports() -> list[dict]:
    city = {a["airport_id"]: a["city"] for a in AIRPORTS}
    return [{"airport_id": i["airportId"], "airport_nm": i["airportNm"], "city": city.get(i["airportId"])}
            for i in _call("GetArprtList", {}) if i.get("airportId")]


def fetch_flights(dep: str, arr: str, day: date) -> list[dict]:
    rows = _call("GetFlightOpratInfoList", {"depAirportId": dep, "arrAirportId": arr, "depPlandTime": day.strftime("%Y%m%d")})
    return [{
        "flight_date": day, "dep_airport_id": dep, "arr_airport_id": arr,
        "dep_airport_nm": r.get("depAirportNm"), "arr_airport_nm": r.get("arrAirportNm"),
        "airline_nm": r.get("airlineNm"), "flight_no": str(r.get("vihicleId") or "-"),
        "dep_time": _hhmm(r.get("depPlandTime")), "arr_time": _hhmm(r.get("arrPlandTime")),
        "economy_charge": int(r["economyCharge"]) or None if r.get("economyCharge") else None,
        "prestige_charge": int(r["prestigeCharge"]) or None if r.get("prestigeCharge") else None,
    } for r in rows]


SAMPLE_AIRLINES = [("대한항공", "KE"), ("아시아나항공", "OZ"), ("제주항공", "7C"), ("진에어", "LJ"), ("티웨이항공", "TW"), ("에어부산", "BX")]


def sample_flights(dep: str, arr: str, day: date) -> list[dict]:
    r = seeded_rng(dep, arr, day)
    rows = []
    for hour in sorted(r.sample(range(6, 21), k=r.randint(4, 8))):
        airline, code = r.choice(SAMPLE_AIRLINES)
        minute = r.choice([0, 10, 20, 30, 40, 50])
        dur = r.choice([55, 60, 65, 70])
        arr_min = hour * 60 + minute + dur
        rows.append({
            "flight_date": day, "dep_airport_id": dep, "arr_airport_id": arr,
            "dep_airport_nm": AIRPORT_NM.get(dep), "arr_airport_nm": AIRPORT_NM.get(arr),
            "airline_nm": airline, "flight_no": f"{code}{r.randint(1100, 1999)}",
            "dep_time": f"{hour:02d}:{minute:02d}", "arr_time": f"{arr_min // 60:02d}:{arr_min % 60:02d}",
            "economy_charge": r.randrange(45000, 130000, 1000), "prestige_charge": r.randrange(90000, 200000, 1000),
        })
    return rows

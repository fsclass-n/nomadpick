"""수집 결과 전송 - direct(DB 직접 적재, 서버 내장 스케줄러) / api(X-RPA-KEY 로 REST 전송, 외부 수집 서버)."""
import base64
import json
from datetime import date, datetime, timedelta

import requests

from backend.app.utils import today_kst

from backend.app.config import settings


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=lambda o: o.isoformat() if isinstance(o, (date, datetime)) else str(o))


class DirectSink:
    def __init__(self) -> None:
        from backend.app.database import SessionLocal, init_db
        from backend.app.services.bootstrap import seed_reference_data

        init_db()
        self.Session = SessionLocal
        with self.Session() as db:
            seed_reference_data(db)

    def _ingest(self, fn_name: str, *args):
        from backend.app.services import ingest

        with self.Session() as db:
            return getattr(ingest, fn_name)(db, *args)

    def products_bulk(self, agency_code: str, collected_at: datetime, source: str, items: list[dict]) -> dict:
        return self._ingest("upsert_products", agency_code, collected_at, source, items)

    def flights(self, items: list[dict], source: str) -> dict:
        return self._ingest("upsert_flights", items, source)

    def airports(self, items: list[dict]) -> dict:
        return self._ingest("upsert_airports", items)

    def log(self, data: dict) -> None:
        self._ingest("add_log", dict(data))

    def report(self, report_date: date, file_name: str, blob: bytes, html: str, summary: dict) -> None:
        self._ingest("save_report", report_date, file_name, blob, html, summary)

    def active_products(self) -> list[dict]:
        from backend.app.services.products import active_products_query, serialize

        with self.Session() as db:
            return [serialize(p) for p in db.scalars(active_products_query()).unique().all()]

    def is_empty(self) -> bool:
        return not self.active_products()


class ApiSink:
    def __init__(self, base_url: str | None = None) -> None:
        self.base = (base_url or settings.api_base_url).rstrip("/") + "/api/v1"
        self.s = requests.Session()
        self.s.headers.update({"X-RPA-KEY": settings.rpa_api_key, "Content-Type": "application/json"})

    def _send(self, method: str, path: str, body: dict) -> dict:
        r = self.s.request(method, f"{self.base}{path}", data=_json(body).encode(), timeout=60)
        r.raise_for_status()
        return r.json()

    def products_bulk(self, agency_code, collected_at, source, items):
        return self._send("POST", "/rpa/products/bulk", {"agency_code": agency_code, "collected_at": collected_at, "source": source, "items": items})

    def flights(self, items, source):
        return self._send("PUT", "/rpa/flights", {"source": source, "items": items})

    def airports(self, items):
        return self._send("PUT", "/rpa/airports", {"items": items})

    def log(self, data):
        self._send("POST", "/rpa/logs", data)

    def report(self, report_date, file_name, blob, html, summary):
        self._send("POST", "/rpa/reports", {"report_date": report_date, "file_name": file_name,
                                            "file_base64": base64.b64encode(blob).decode(), "chart_html": html, "summary": summary})

    def active_products(self) -> list[dict]:
        items, page = [], 1
        while True:
            r = self.s.get(f"{self.base}/products", params={"page": page, "size": 100, "sort": "depart"}, timeout=30)
            r.raise_for_status()
            data = r.json()
            items += data["items"]
            if page * 100 >= data["total"]:
                return items
            page += 1

    def is_empty(self) -> bool:
        r = self.s.get(f"{self.base}/meta", timeout=30)
        r.raise_for_status()
        return r.json()["total"] == 0


def get_sink(kind: str | None = None):
    return ApiSink() if (kind or settings.rpa_sink) == "api" else DirectSink()


def domestic_departures(products: list[dict], days: int = 30) -> set[tuple[str, date]]:
    today = today_kst()
    limit = today + timedelta(days=days)
    out = set()
    for p in products:
        if not (p.get("is_domestic") and p.get("city")):
            continue
        day = date.fromisoformat(p["depart_date"])
        if p.get("depart_end"):  # 출발 기간 상품은 다음 출발 가능일
            day = max(day, today)
        if day <= limit:
            out.add((p["city"], day))
    return out

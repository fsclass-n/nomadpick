"""여행사별 파서 (하나투어 · 모두투어 · 노랑풍선) - Playwright 로 렌더링된 실제 페이지 구조 기준."""
import json
import logging

from bs4 import BeautifulSoup, Tag

from .base import BaseCollector

log = logging.getLogger(__name__)


class HanatourCollector(BaseCollector):
    """하나투어 기획전(/promotion/plan/...).

    카드(div.card-wrap)의 id(productInfo_-18_24300)는 '노출 순번_기획전번호'라 상품코드가 아니고 순서가 바뀌면 달라진다.
    → 브라우저로 기획전을 연 뒤, 화면이 사용하는 기획전 데이터(JSON)를 같은 브라우저 세션으로 받아
      HTTP 엔진과 같은 변환(대표상품코드·출발 기간·이미지)을 사용한다. 실패 시에만 카드 HTML 로 대체.
    """
    agency = "hanatour"

    def postprocess(self, row: dict, item: Tag) -> dict:
        if row.get("code"):
            row["code"] = row["code"].replace("productInfo_", "HT")
        return row

    async def browser_rows(self, session, url: str, page) -> list[dict]:
        from .http_engine import hanatour_plan_api, hanatour_plan_rows

        try:
            rows = hanatour_plan_rows(await session.fetch_json(hanatour_plan_api(url), referer=page.url), url)
            if rows:
                return self.exclude(rows)
        except Exception as e:  # noqa: BLE001 - 데이터 API 실패 시 카드 HTML 로 대체
            log.warning("[hanatour] 기획전 데이터 요청 실패 - 카드 HTML 로 대체: %s", str(e)[:120])
        return self.parse(page.html, page.url)


class ModetourCollector(BaseCollector):
    """모두투어 기획전(/promotion/{번호}) - Next.js __NEXT_DATA__ 에 포함된 상품 JSON."""
    agency = "modetour"

    @staticmethod
    def _get(obj, path: str):
        """'productCodes[0].marketingAirName' 형식 경로 조회."""
        for part in path.split("."):
            name, _, idx = part.rstrip("]").partition("[")
            obj = obj.get(name) if isinstance(obj, dict) else None
            if idx:
                obj = obj[int(idx)] if isinstance(obj, list) and len(obj) > int(idx) else None
        return obj

    def parse(self, html: str, page_url: str) -> list[dict]:
        tag = BeautifulSoup(html, "html.parser").find("script", id="__NEXT_DATA__")
        if tag is None or not tag.string:
            return []
        f = self.conf["fields"]
        rows, seen = [], set()

        def walk(o):
            if isinstance(o, dict):
                code, title = o.get(f["code"]), o.get(f["title"])
                if code and title and o.get(f["price"]):
                    dates = o.get(f["dates"]) or [{}]
                    departures = sorted(o.get(f["departure_dates"]) or [])  # 기획전: 출발 가능일 목록
                    depart = o.get(f["depart"]) or (departures[0] if departures else None)
                    key = (code, depart)
                    if key not in seen:
                        seen.add(key)
                        first = dates[0] if dates else {}
                        rows.append({
                            "code": str(code), "title": str(title), "price": str(o.get(f["price"])),
                            "depart": depart, "depart_end": departures[-1] if len(departures) > 1 else None,
                            "duration": f'{first.get("night")}박{first.get("days")}일' if first.get("days") else None,
                            "origin": "/".join(o.get(f["origin"]) or []), "airline": self._get(o, f["airline"]),
                            "image": o.get(f["image"]), "link": page_url,
                        })
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(json.loads(tag.string))
        return self.exclude(rows)


class YbtourCollector(BaseCollector):
    """노랑풍선 기획전 - 긴급특가 ul.list_thum > li(정상가 p.price·특가 p.sale 동시 표기), 국내 ul.list_prod > li.item."""
    agency = "ybtour"

    def postprocess(self, row: dict, item: Tag) -> dict:
        tit = item.select_one("p.tit")
        if tit is not None:  # 두 번째 줄('ㄴ10만원 할인')은 홍보 문구이므로 제외
            row["title"] = tit.get_text("\n", strip=True).split("\n")[0]
        return row


COLLECTORS = [HanatourCollector, ModetourCollector, YbtourCollector]
COLLECTOR_BY_AGENCY = {c.agency: c for c in COLLECTORS}

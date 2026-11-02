"""경량 HTTP 엔진 파서 - 여행사 공개 JSON 응답 형식 기준 (네트워크 없이 가짜 세션으로 검증)."""
from rpa.collector import http_engine
from rpa.collector.agencies import HanatourCollector, YbtourCollector


class FakeResp:
    def __init__(self, data=None, text=""):
        self._data, self.text = data, text

    def json(self):
        return self._data


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, **kw):
        self.calls.append(url)
        return next(v for k, v in self.routes.items() if k in url)

    post = get


def test_hanatour_plan_json_to_rows():
    item = {"title": "오사카/교토 3,4일 #온천", "price": "779,900", "orgPrice": 899000, "productCodeInLink": "MJO1119",
            "travelDaysList": ["3", "4"], "startAt": "2026.11.09 00:00:00", "endAt": "2026.12.09 00:00:00",
            "linkTypeUrl_2": "/package/major-products?rprsProdCds=MJO1119&strtDepDay=20261109&endDepDay=20261231"}
    plan = {"data": {"componentList": [{"content": {"itemList": [item, dict(item), {"title": "항공권 특가", "price": 1}]}}]}}
    http = FakeHttp({"gw.hanatour.com": FakeResp(plan)})
    home = 'urlAdrs:"/promotion/plan/PM006787B572",menuNm:"임박특가"'
    rows = http_engine.hanatour(HanatourCollector(), http, home, "https://www.hanatour.com/")
    assert len(rows) == 1                                    # 같은 상품·출발일 중복 제거, 항공권 제외
    r = rows[0]
    assert r["code"] == "HTMJO1119" and r["price"] == "779900" and r["original_price"] == "899000"
    assert (r["depart"], r["depart_end"], r["duration"]) == ("2026-11-09", "2026-12-31", "3,4일")
    assert r["link"].startswith("https://www.hanatour.com/package/major-products")


def test_ybtour_soldout_json_to_rows():
    goods = [{"goodsCd": "ATP1132", "showNm": "방콕/파타야 5/6일<BR> ㄴ10만원 할인", "price": 349000, "discPrice": 249000,
              "beneNote": "<EM>#긴급특가: 11/2,3,6</EM><BR>#알카자쇼", "soldOutYn": "N", "imgUrl": "https://img/x.jpg"},
             {"goodsCd": "SOLD1", "showNm": "마감 상품", "price": 1, "soldOutYn": "Y"}]
    http = FakeHttp({"promotionDetail": FakeResp(text="var templateNo = '1000039266';"),
                     "soldOutTemplate": FakeResp({"soldOutGoodsList": goods})})
    home = '<a href="https://pkg.ybtour.co.kr/promotion/promotionDetail.yb?mstNo=1">긴급특가</a>'
    rows = http_engine.ybtour(YbtourCollector(), http, home, "https://www.ybtour.co.kr/")
    codes = [r["code"] for r in rows]
    assert "ATP1132" in codes and "SOLD1" not in codes       # 매진 제외
    r = rows[codes.index("ATP1132")]
    assert r["title"] == "방콕/파타야 5/6일" and r["price"] == "249000" and r["original_price"] == "349000"
    assert r["depart"] == "11/2,3,6"

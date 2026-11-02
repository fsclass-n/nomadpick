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
            "mediaList": [{"type": "IMAGE", "url": "https://image.hanatour.com/x.jpg"}],
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
    assert r["image"] == "https://image.hanatour.com/x.jpg"  # mediaList 이미지


def test_hanatour_browser_engine_uses_same_data_and_codes():
    """브라우저 엔진도 같은 기획전 데이터·변환 → HTTP 엔진과 상품코드·출발일·이미지가 같다 (카드 id 순번 미사용)."""
    import asyncio

    plan = {"itemList": [{"title": "마나도 5일", "price": 599000, "productCodeInLink": "MAD1196", "itemId": -18,
                          "linkTypeUrl_2": "/package/major-products?rprsProdCds=MAD1196&strtDepDay=20261101&endDepDay=20261231",
                          "mediaList": [{"type": "IMAGE", "url": "https://image.hanatour.com/m.jpg"}]}]}

    class FakeSession:
        async def fetch_json(self, url, referer=None):
            assert "gw.hanatour.com/dcr/promotions/plan/PM006787B572" in url
            return plan

    class Page:
        url, html = "https://www.hanatour.com/promotion/plan/PM006787B572", '<div class="card-wrap" id="productInfo_-18_24300"></div>'

    url = "https://www.hanatour.com/promotion/plan/PM006787B572"
    rows = asyncio.run(HanatourCollector().browser_rows(FakeSession(), url, Page()))
    http_rows = http_engine.hanatour_plan_rows(plan, url)
    assert [(r["code"], r["depart"], r["depart_end"], r["image"]) for r in rows] == \
           [(r["code"], r["depart"], r["depart_end"], r["image"]) for r in http_rows] == \
           [("HTMAD1196", "2026-11-01", "2026-12-31", "https://image.hanatour.com/m.jpg")]

    class FailSession:
        async def fetch_json(self, url, referer=None):
            raise RuntimeError("HTTP 403")

    fallback = asyncio.run(HanatourCollector().browser_rows(FailSession(), url, Page()))
    assert [r["code"] for r in fallback] == ["HT-18_24300"]  # 데이터 요청 실패 시에만 카드 HTML 로 대체


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
    assert r["depart"] == "#긴급특가: 11/2,3,6"  # 화면 카드(p.txt em)와 같은 문구 → 브라우저 엔진과 같은 출발일


def test_ybtour_depart_list_across_months_matches_browser():
    """'11/22,23,28,30,12/2,3' 을 12에서 끊지 않는다 (이전: 11/12 로 잘못 해석)."""
    from datetime import date

    from rpa.cleaner.normalize import parse_depart

    goods = [{"goodsCd": "AVP1202", "showNm": "하노이&하롱베이 5일", "price": 599000,
              "beneNote": "<EM>#긴급특가: 11/22,23,28,30,12/2,3</EM><BR>#하롱베이 크루즈", "soldOutYn": "N"}]
    row = http_engine.ybtour_goods_rows(goods, "https://pkg.ybtour.co.kr/promotion/x", set())[0]
    browser_text = "#긴급특가: 11/22,23,28,30,12/2,3"  # 같은 상품 화면 카드 문구
    ref = date(2026, 11, 2)
    assert parse_depart(row["depart"], ref) == parse_depart(browser_text, ref) == (date(2026, 11, 22), date(2026, 12, 3))


def test_ybtour_http_also_reads_server_rendered_list():
    html = ('var templateNo = "1000039266";<ul class="list_prod"><li class="item" data-braze-temp-goods-cd="KJF3658">'
            '<p class="tit">제주 3일</p><p class="term"><span class="date">2026.11.08 ~ 2027.03.14</span></p>'
            '<p class="price"><em>299,000</em></p></li></ul>')
    http = FakeHttp({"promotionDetail": FakeResp(text=html), "soldOutTemplate": FakeResp({"soldOutGoodsList": []})})
    home = '<a href="https://pkg.ybtour.co.kr/promotion/promotionDetail.yb?mstNo=1">긴급특가</a>'
    rows = http_engine.ybtour(YbtourCollector(), http, home, "https://www.ybtour.co.kr/")
    assert "KJF3658" in [r["code"] for r in rows]

from datetime import date, datetime

from rpa.cleaner.normalize import clean
from rpa.collector import browser as browser_mod
from rpa.collector.agencies import COLLECTORS, HanatourCollector, ModetourCollector, YbtourCollector
from rpa.collector.robots import RobotsPolicy
from rpa.collector.sample_site import build_items, parse_sample, render_page
from rpa.public_data import molit_flight

AT = datetime(2026, 11, 18, 14, 30)
REF = AT.date()

# 실제 페이지(Playwright 렌더링 결과)에서 발췌한 구조
HANATOUR_HTML = """<div class="card-list-wrap medium">
<div class="card-wrap" id="productInfo_-18_24300"><div class="section static"><div class="section"><div class="label-group">
<span class="label time pink">11.01~12.31 출발</span></div></div></div><div class="section"><div class="text-group">
<p class="eps2">마나도 5일 #부나켄호핑투어 #선셋투어</p></div><div class="option-group"><span>인천</span><span>5일</span></div>
<div class="price-group"><span class="price"><strong>599,000</strong>원~</span></div></div></div>
<div class="card-wrap" id="productInfo_-5_24300"><div class="section"><div class="label-group"><span class="label time">11.03~11.30 출발</span></div></div>
<div class="section"><div class="text-group"><p class="eps2">서울↔후쿠오카 왕복 항공권</p></div>
<div class="price-group"><span class="price"><strong>25만원대</strong>~</span></div></div></div></div>"""

YBTOUR_HTML = """<ul class="list_thum"><li data-braze-temp-goods-cd="EWP4138"><a href="#yb"><div class="txt_content">
<p class="tit">이탈리아 일주 9일 TW<br/>ㄴ10만원 할인★최저가★</p><p class="txt"><em>#긴급특가: 11/4, 11, 25</em><br/>#10대특식</p>
<div class="box_price"><p class="price"><em>2,490,000</em>원~</p><p class="sale"><em>2,390,000</em>원~</p></div></div></a></li></ul>"""

MODETOUR_HTML = """<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"initialState":{"api":{"mutations":{"m":{"data":
{"result":{"productMasters":[{"masterCode":"MAT260929030","masterProductName":"★초특가핫딜★ 코타키나발루 준특급 노쇼핑 5/6일",
"price":449000,"minDepartureDate":null,"dates":null,"depatureFrom":null,"productCodes":null,
"departureDates":["2026-11-20","2026-11-27","2027-01-15"]},
{"masterCode":"MAT260821028","masterProductName":"[좌석확보] 오사카/나라/교토/고베 3일","price":599900,
"minDepartureDate":"2026-12-01T00:00:00","dates":[{"night":2,"days":3}],"depatureFrom":["인천"],
"productCodes":[{"marketingAirName":"트리니티 항공"}]}]}}}}}}}}}</script>"""


def test_hanatour_real_markup():
    items, failed, _ = clean(HanatourCollector().parse(HANATOUR_HTML, "https://www.hanatour.com/promotion/plan/X"), REF)
    assert failed == 0 and len(items) == 1  # 왕복 항공권은 제외 키워드로 수집 대상에서 빠짐
    it = items[0]
    assert it["product_code"] == "HT-18_24300" and it["title"] == "마나도 5일"
    assert (it["region"], it["price"], it["nights"], it["days"]) == ("동남아", 599000, 4, 5)
    assert (it["depart_date"], it["depart_end"]) == (date(2026, 11, 1), date(2026, 12, 31))
    assert it["detail_url"] == "https://www.hanatour.com/promotion/plan/X"


def test_ybtour_prefers_sale_price():
    """BUG-01 회귀 테스트: 정상가(p.price)·특가(p.sale)가 함께 표기되면 특가를 판매가로 저장."""
    items, _, _ = clean(YbtourCollector().parse(YBTOUR_HTML, "https://pkg.ybtour.co.kr/p"), REF)
    it = items[0]
    assert it["title"] == "이탈리아 일주 9일 TW"
    assert (it["price"], it["original_price"]) == (2390000, 2490000)
    assert (it["depart_date"], it["depart_end"], it["days"]) == (date(2026, 11, 4), date(2026, 11, 25), 9)


def test_modetour_next_data_json():
    items, failed, _ = clean(ModetourCollector().parse(MODETOUR_HTML, "https://www.modetour.com/promotion/1"), REF)
    assert failed == 0
    by_code = {i["product_code"]: i for i in items}
    kk = by_code["MAT260929030"]
    assert (kk["city"], kk["price"], kk["days"]) == ("코타키나발루", 449000, 5)
    assert (kk["depart_date"], kk["depart_end"]) == (date(2026, 11, 20), date(2027, 1, 15))
    osa = by_code["MAT260821028"]
    assert (osa["title"], osa["nights"], osa["days"], osa["airline"]) == ("오사카/나라/교토/고베 3일", 2, 3, "트리니티 항공")


def test_sample_pages_use_same_parsers():
    for cls in COLLECTORS:
        c = cls()
        rows = parse_sample(c.agency, AT)
        items, failed, _ = clean(rows, AT.date())
        expected = build_items(c.agency, AT)
        assert failed == 0 and len(items) == len(expected) > 40, c.agency
        prices = {(e["code"], e["depart"]): e["price"] for e in expected}
        for it in items:
            code = it["product_code"].removeprefix("HTproductInfo_").removeprefix("HT")
            key = next(k for k in prices if k[1] == it["depart_date"] and k[0].endswith(code.split("-")[-1]))
            assert it["price"] == prices[key], c.agency


def test_sample_prices_change_by_time_slot():
    a = {(i["code"], i["depart"]): i["price"] for i in build_items("hanatour", AT)}
    b = {(i["code"], i["depart"]): i["price"] for i in build_items("hanatour", AT.replace(hour=20))}
    assert a.keys() == b.keys() and a != b
    assert "card-wrap" in render_page("hanatour", AT)


def test_discover_deal_pages_from_home():
    c = HanatourCollector()
    home = 'menu:{urlAdrs:"\\u002Fpromotion\\u002Fplan\\u002FPM0001",menuId:"x",menuNm:"임박특가"}'
    assert c.discover(home) == ["https://www.hanatour.com/promotion/plan/PM0001"]
    assert c.discover("<html></html>") == c.conf["list_urls"]
    m = ModetourCollector()
    assert m.discover('"link":"/promotion/1557","x":1,"link":"https://www.modetour.com/promotion/1542"') == [
        "https://www.modetour.com/promotion/1557", "https://www.modetour.com/promotion/1542"]


def test_retry_with_backoff():
    sleeps, calls = [], {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("HTTP 403")
        return "ok"

    assert browser_mod.retry(flaky, "https://x.test", sleep=sleeps.append) == ("ok", 2)
    assert sleeps == [2, 4]

    sleeps.clear()
    try:
        browser_mod.retry(lambda: (_ for _ in ()).throw(RuntimeError("timeout")), "https://x.test", sleep=sleeps.append)
        raise AssertionError("BrowserError expected")
    except browser_mod.BrowserError as e:
        assert e.retries == 3
    assert sleeps == [2, 4, 8]


def test_robots_policy_rfc9309():
    rules = RobotsPolicy(200, "User-agent: *\nDisallow: /api/\nDisallow: /mypage/\n")
    assert rules.mode == "rules"
    assert rules.allowed("https://www.ybtour.co.kr/promotion/1") and not rules.allowed("https://www.ybtour.co.kr/api/list")
    assert RobotsPolicy(403, "<HTML>Access Denied</HTML>").allowed("https://www.modetour.com/")  # 4xx: 제한 없음
    assert RobotsPolicy(404).allowed("https://x.test/a")
    assert not RobotsPolicy(503).allowed("https://x.test/a")  # 5xx: 전체 비허용
    assert not RobotsPolicy(None).allowed("https://x.test/a")


def test_molit_items_shapes():
    ok = {"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": {"vihicleId": "KE1201"}}}}}
    assert molit_flight._items(ok) == [{"vihicleId": "KE1201"}]
    assert molit_flight._items({"response": {"header": {"resultCode": "00"}, "body": {"items": ""}}}) == []
    try:
        molit_flight._items({"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}}})
        raise AssertionError
    except molit_flight.PublicApiError as e:
        assert "30" in str(e)
    assert molit_flight._hhmm(202611181030) == "10:30"

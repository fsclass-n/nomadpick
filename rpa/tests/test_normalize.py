from datetime import date

import pytest

from rpa.cleaner.normalize import (classify_city, classify_theme, clean, parse_date, parse_duration, parse_price,
                                   parse_seats)

REF = date(2026, 11, 11)


@pytest.mark.parametrize("text, expected", [
    ("1,290,000원~", 1290000), ("699,000원", 699000), ("129만원", 1290000), ("특가 99만", 990000),
    ("69.9만원", 699000), ("특가 69.9만", 699000), ("정상가 1,190,000원", 1190000), ("1290000", 1290000),
    ("  459,000 원 ~ ", 459000), ("₩899,000", 899000), ("최저 1,890,000원부터", 1890000), ("3,290,000", 3290000),
    ("189만 원", 1890000), ("12.5만원", 125000), ("특가 159,000원", 159000), ("판매가: 2,190,000원", 2190000),
    ("가격문의", None), ("", None), (None, None), ("100원", None), ("1.2만", 12000), ("99만9천원", 999000),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("3박 5일", (3, 5)), ("3박5일", (3, 5)), ("4일", (3, 4)), ("7박 9일", (7, 9)), ("1박2일", (1, 2)), ("당일", (None, None)), (None, (None, None)),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("2026.12.05(토) 출발", date(2026, 12, 5)), ("2026-12-05", date(2026, 12, 5)), ("2026년 12월 5일 (토)", date(2026, 12, 5)),
    ("12/12(금) 출발", date(2026, 12, 12)), ("12월 5일", date(2026, 12, 5)),
    ("01/08 출발", date(2027, 1, 8)),  # 연도 없는 과거 월 → 다음 해
    ("2026.02.30", None), ("미정", None),
])
def test_parse_date(text, expected):
    assert parse_date(text, REF) == expected


@pytest.mark.parametrize("text, expected", [("잔여 6석", 6), ("6석 남음", 6), ("마감", 0), ("12", 12), ("", None), (None, None)])
def test_parse_seats(text, expected):
    assert parse_seats(text) == expected


def test_classify_city_and_theme():
    assert classify_city("[특가] 다낭·호이안 풀빌라 3박5일") == ("다낭", "동남아", "VN")
    assert classify_city("오사카·교토 핵심 관광") == ("오사카", "일본", "JP")
    assert classify_city("제주 골프 36홀") == ("제주", "국내", "KR")
    assert classify_city("알 수 없는 상품") == (None, None, None)
    assert classify_city("[부산] 세부 5일 제이파크")[0] == "세부"  # 국내 도시는 출발지로 간주
    assert classify_city("(부산출발) 대마도 2일")[:2] == ("대마도", "일본")
    assert classify_city("[오사카] 교토/고베 3일")[0] == "오사카"
    assert classify_city("[포항]울릉도/독도 3일 #쾌속선") == ("울릉도", "국내", "KR")  # 국내끼리는 [출발지] 라벨 다음 지명
    assert classify_city("충남/공주 1일 #마곡사")[:2] == ("공주", "국내")
    assert classify_city("서귀포 신라호텔 3일")[0] == "제주"  # 세부 지명 → 대표 도시
    assert classify_city("[인천/부산/제주] 싱가포르 5일")[0] == "싱가포르"
    assert classify_theme("치앙마이 골프 54홀") == "골프"
    assert classify_theme("장가계 부모님 효도여행") == "효도"
    assert classify_theme("타이베이 자유여행 에어텔") == "자유여행"
    assert classify_theme("푸켓 풀빌라 휴양") == "휴양"
    assert classify_theme("파리 시내 일주") == "관광"


def test_clean_dedupes_and_counts_failures():
    raw = [
        {"code": "A1", "title": "[특가] 다낭 풀빌라 3박5일", "depart": "2026.12.05", "duration": "3박 5일", "price": "699,000원~", "original_price": "1,029,000원", "seats": "잔여 6석"},
        {"code": "A1", "title": "[특가] 다낭 풀빌라 3박5일", "depart": "2026.12.05", "duration": "3박 5일", "price": "699,000원~", "original_price": "1,029,000원", "seats": "잔여 6석"},
        {"code": "A2", "title": "오사카 관광", "depart": "12/12", "duration": "3일", "price": "45.9만원", "original_price": "40만원", "seats": "마감"},
        {"code": "A3", "title": "가격 없는 괌 상품", "depart": "2026.12.05", "price": "문의"},
        {"code": "A4", "title": "도시 없음 상품", "depart": "2026.12.05", "price": "500,000원"},
        {"code": "A5", "title": "지난 출발 방콕", "depart": "2026.10.01", "price": "500,000원"},
    ]
    items, failed, _ = clean(raw, REF)
    assert failed == 2
    assert [i["product_code"] for i in items] == ["A1", "A2"]
    first, second = items
    assert first["title"] == "다낭 풀빌라 3박5일" and first["price"] == 699000 and first["original_price"] == 1029000
    assert (first["nights"], first["days"], first["seats_left"], first["region"]) == (3, 5, 6, "동남아")
    assert second["original_price"] is None  # 정상가 ≤ 판매가 → 무시
    assert (second["nights"], second["days"], second["seats_left"]) == (2, 3, 0)


@pytest.mark.parametrize("text, expected", [
    ("11.01~12.31 출발", (date(2026, 11, 1), date(2026, 12, 31))),
    ("11.01~03.31 출발", (date(2026, 11, 1), date(2027, 3, 31))),
    ("#긴급특가: 11/12, 14", (date(2026, 11, 12), date(2026, 11, 14))),
    ("#긴급특가: 11/10,17,9,21,24", (date(2026, 11, 9), date(2026, 11, 24))),
    ("#긴급특가: 10/27 11/3,10", (date(2026, 10, 27), date(2026, 11, 10))),
    ("#긴급특가: 11/12 #가족 3일", (date(2026, 11, 12), None)),
    ("2026-12-01T00:00:00", (date(2026, 12, 1), None)),
    ("2026.10.30 ~ 2026.11.29", (date(2026, 10, 30), date(2026, 11, 29))),
    ("#긴급특가: 10월~", (None, None)),
])
def test_parse_depart_ranges_and_lists(text, expected):
    from rpa.cleaner.normalize import parse_depart
    assert parse_depart(text, date(2026, 10, 26)) == expected


@pytest.mark.parametrize("text, expected", [("3,4일", (2, 3)), ("5/6일", (4, 5)), ("3/4/5일", (2, 3))])
def test_parse_duration_multi_option(text, expected):
    assert parse_duration(text) == expected


def test_clean_empty():
    assert clean([], REF)[:2] == ([], 0)


def test_undated_domestic_is_anytime_but_overseas_fails():
    raw = [{"code": "D1", "title": "홍도/흑산도 3일 #유람선", "price": "364,000"},
           {"code": "O1", "title": "동유럽 3국 7일", "price": "1,999,000"}]
    items, failed, _ = clean(raw, REF)
    assert failed == 1 and len(items) == 1
    it = items[0]
    assert (it["region"], it["depart_date"], it["depart_end"]) == ("국내", REF, date(2027, 1, 10))  # 수집일 ~ +60일
    assert it["depart_anytime"] is True
    dated, _, _ = clean([{"code": "D2", "title": "제주 3일", "depart": "12/01", "price": "300,000"}], REF)
    assert dated[0]["depart_anytime"] is False


@pytest.mark.parametrize("src, page, expected", [
    ("https://img.x.com/a.jpg", None, "https://img.x.com/a.jpg"),
    ("//dimgcdn.x.co.kr/a.jpg", "https://pkg.x.co.kr/p", "https://dimgcdn.x.co.kr/a.jpg"),
    ("/usr/cms/a.jpg", "https://www.hanatour.com/promotion/plan/X", "https://www.hanatour.com/usr/cms/a.jpg"),
    ("data:image/gif;base64,R0lGOD", "https://x.com", None), ("", "https://x.com", None), (None, None, None),
])
def test_image_url(src, page, expected):
    from rpa.cleaner.normalize import image_url
    assert image_url(src, page) == expected

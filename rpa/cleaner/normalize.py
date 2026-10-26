"""pandas 정제·표준화 - 가격/일정/출발일(기간·목록)/잔여석 표기 통일, 지역·테마 분류, 중복 제거."""
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..catalog import CITY_INFO, THEME_KEYWORDS

_CITY_KEYS = sorted(CITY_INFO, key=len, reverse=True)
_LABEL_RE = re.compile(r"^\s*\[[^\]]+\]\s*")


def parse_price(text: str | None) -> int | None:
    """'1,290,000원~', '129만원', '특가 99.9만', '정상가 1,190,000원' → 원 단위 정수."""
    if not text:
        return None
    t = str(text).replace(",", "").replace(" ", "")
    if m := re.search(r"(\d+)만(\d)천", t):  # 99만9천원
        return int(m.group(1)) * 10_000 + int(m.group(2)) * 1_000
    if m := re.search(r"(\d+(?:\.\d+)?)만", t):
        return int(round(float(m.group(1)) * 10_000))
    m = re.search(r"(\d{4,})", t)
    return int(m.group(1)) if m else None


def parse_duration(text: str | None) -> tuple[int | None, int | None]:
    """'3박 5일', '3박5일' → (3, 5) / '4일' → (3, 4) / '3,4일'·'3/4/5일'(복수 일정) → 첫 일정 (2, 3)."""
    if not text:
        return None, None
    t = str(text).replace(" ", "")
    if m := re.search(r"(\d+)박(\d+)일", t):
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"(\d+)(?:[,/]\d+)+일", t):
        days = int(m.group(1))
        return max(days - 1, 0), days
    if m := re.search(r"(\d+)일", t):
        days = int(m.group(1))
        return max(days - 1, 0), days
    return None, None


def parse_date(text: str | None, ref: date) -> date | None:
    """'2026.12.05(토)', '2026-12-05', '2026년 12월 5일', '12/12(금)', '12월 5일' → date (연도 없으면 추정)."""
    if not text:
        return None
    t = str(text)
    if m := re.search(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", t):
        y, mo, d = map(int, m.groups())
    elif m := re.search(r"(\d{1,2})\s*[/.월]\s*(\d{1,2})", t):
        mo, d = map(int, m.groups())
        y = ref.year
        try:
            if date(y, mo, d) < ref - timedelta(days=30):
                y += 1
        except ValueError:
            return None
    else:
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


_LIST_NEXT = re.compile(r"[\s,]+(?:(\d{1,2})/)?(\d{1,2})(?![\d~])")


def _infer(mo: int, d: int, ref: date) -> date | None:
    """연도 없는 월/일 → 기준일 60일 이전이면 다음 해로 추정."""
    try:
        v = date(ref.year, mo, d)
    except ValueError:
        return None
    return date(ref.year + 1, mo, d) if v < ref - timedelta(days=60) else v


def parse_depart(text: str | None, ref: date) -> tuple[date | None, date | None]:
    """출발일 표기 → (첫 출발일, 마지막 출발일).

    '11.01~12.31 출발'(기간, 하나투어) / '#긴급특가: 11/4, 11'·'10/26,28,11/10'(날짜 목록, 노랑풍선)
    / '2026-11-01T00:00:00'(모두투어 JSON) / '2026.12.05(토)'·'12/12' 단일 날짜.
    """
    if not text:
        return None, None
    t = str(text)
    if re.search(r"20\d{2}\s*[.\-/년]", t):
        d = parse_date(t, ref)
        return d, None
    if m := re.search(r"(\d{1,2})\.(\d{1,2})\s*~\s*(\d{1,2})\.(\d{1,2})", t):
        start, end = _infer(int(m[1]), int(m[2]), ref), _infer(int(m[3]), int(m[4]), ref)
        if start and end and end < start:
            end = date(end.year + 1, end.month, end.day)
        return start, end
    if m := re.search(r"(\d{1,2})/(\d{1,2})", t):
        month, dates, pos = int(m[1]), [_infer(int(m[1]), int(m[2]), ref)], m.end()
        while nxt := _LIST_NEXT.match(t, pos):  # 이어지는 ', 13' · ' 11/3' 토큰만 읽고 다른 문구가 나오면 중단
            month = int(nxt[1]) if nxt[1] else month
            dates.append(_infer(month, int(nxt[2]), ref))
            pos = nxt.end()
        dates = sorted(x for x in dates if x)
        if not dates:
            return None, None
        return dates[0], (dates[-1] if dates[-1] != dates[0] else None)
    return parse_date(t, ref), None


def parse_seats(text: str | None) -> int | None:
    if text is None or str(text).strip() == "":
        return None
    t = str(text)
    if "마감" in t:
        return 0
    m = re.search(r"(\d+)", t)
    return int(m.group(1)) if m else None


_ORIGIN_RE = re.compile(r"[가-힣]+\s?출발")


def classify_city(title: str) -> tuple[str | None, str | None, str | None]:
    """상품명에서 가장 먼저 등장하는 도시 → (도시, 지역, 국가코드).

    '청주출발'·'부산 출발' 같은 출발지는 제외하고, 국내·해외 도시가 함께 있으면('[부산] 세부 5일')
    국내 도시는 출발지로 보고 해외 도시를 목적지로 선택한다.
    """
    title = _ORIGIN_RE.sub(" ", title)
    found = [(title.find(k), k) for k in _CITY_KEYS if k in title]
    if not found:
        return None, None, None
    overseas = [f for f in found if CITY_INFO[f[1]][0] != "국내"]
    city = min(overseas or found)[1]
    region, country = CITY_INFO[city]
    return city, region, country


def classify_theme(title: str) -> str:
    for theme, words in THEME_KEYWORDS:
        if any(w in title for w in words):
            return theme
    return "관광"


def clean_title(title: str) -> str:
    """'[특가] 오사카/교토 3,4일 #교토온천호텔 #묘도인' → '오사카/교토 3,4일' (앞쪽 라벨·뒤쪽 해시태그 제거)."""
    t = _LABEL_RE.sub("", title).strip()
    head = t.split(" #")[0].strip()
    return head if len(head) >= 4 else t


def _none(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT else v


def clean(raw: list[dict], ref: date) -> tuple[list[dict], int, pd.DataFrame]:
    """원시 행 → (적재용 항목, 정제 실패 건수, 정제 DataFrame)."""
    if not raw:
        return [], 0, pd.DataFrame()
    df = pd.DataFrame(raw)
    for col in ("code", "title", "link", "depart", "duration", "price", "original_price", "seats", "airline"):
        if col not in df:
            df[col] = None
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["price_num"] = df["price"].map(parse_price)
    df["original_num"] = df["original_price"].map(parse_price)
    if "depart_end" not in df:
        df["depart_end"] = None
    df[["depart_date", "depart_end"]] = pd.DataFrame(
        [(s, parse_date(e, ref) if isinstance(e, str) and e else end) for (s, end), e in
         zip((parse_depart(t, ref) for t in df["depart"]), df["depart_end"])], index=df.index)
    df[["nights", "days"]] = pd.DataFrame(
        [parse_duration(d) if parse_duration(d)[1] else parse_duration(t) for d, t in zip(df["duration"], df["title"])],
        index=df.index)
    df[["city", "region", "country_code"]] = pd.DataFrame(df["title"].map(classify_city).tolist(), index=df.index)
    df["theme"] = df["title"].map(classify_theme)
    df["seats_left"] = df["seats"].map(parse_seats)

    valid = df["code"].notna() & (df["title"] != "") & df["price_num"].notna() & df["depart_date"].notna() & df["region"].notna()
    failed = int((~valid).sum())
    df = df.loc[valid].copy()
    last_day = [e if _none(e) is not None else s for s, e in zip(df["depart_date"], df["depart_end"])]
    df = df.loc[[d >= ref for d in last_day]]  # 출발 기간이 끝난 상품 제외
    df = df.drop_duplicates(["code", "depart_date"])  # 여러 기획전 중복 노출 제거
    df.loc[df["original_num"] <= df["price_num"], "original_num"] = np.nan
    df["title"] = df["title"].map(clean_title)

    items = [{
        "product_code": str(r.code)[:50],
        "title": r.title[:200],
        "region": r.region,
        "country_code": r.country_code,
        "city": r.city,
        "theme": r.theme,
        "depart_date": r.depart_date,
        "depart_end": _none(r.depart_end),
        "nights": int(r.nights) if _none(r.nights) is not None else None,
        "days": int(r.days) if _none(r.days) is not None else None,
        "price": int(r.price_num),
        "original_price": int(r.original_num) if _none(r.original_num) is not None else None,
        "seats_left": int(r.seats_left) if _none(r.seats_left) is not None else None,
        "airline": _none(r.airline),
        "image_url": None,
        "detail_url": _none(r.link),
    } for r in df.itertuples()]
    return items, failed, df

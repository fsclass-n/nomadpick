"""브라우저 없이 수집하는 경량 HTTP 엔진 (RPA_ENGINE=http, 기본값).

Render 무료(512MB · 0.1 CPU)에서도 동작하도록 Chromium 대신 각 여행사 웹페이지가 내부적으로 호출하는
공개 데이터(JSON API · 서버 렌더링 JSON)를 requests 로 직접 받는다. → 메모리 수십 MB, 1회 수집 수십 초.
  하나투어 : 홈 HTML 에서 특가 기획전 코드 탐색 → gw.hanatour.com/dcr/promotions/plan/{코드} (기획전 상품 JSON)
  모두투어 : 홈 HTML 에서 기획전 탐색 → 기획전 페이지 __NEXT_DATA__ (Next.js 서버 렌더링 JSON)
  노랑풍선 : 홈 HTML 에서 긴급특가 기획전 탐색 → 기획전 템플릿 번호 → soldOutTemplate.ajax (상품 JSON)
수집 예의는 브라우저 엔진과 동일: robots.txt(RFC 9309) 확인, 요청 간 REQUEST_INTERVAL_SEC 이상, 실패 시 재시도(2·4·8초).
"""
import logging
import random
import re
import time
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from backend.app.config import settings

from .browser import BrowserError, retry
from .robots import RobotsPolicy, robots_url

log = logging.getLogger(__name__)


class HttpSession:
    """여행사 1곳 수집용 requests 세션 (쿠키 유지 · 브라우저와 같은 헤더 · 요청 간격 · robots.txt)."""

    def __init__(self) -> None:
        ua = settings.rpa_user_agent
        major = ua.split("Chrome/")[-1].split(".")[0] if "Chrome/" in ua else "131"
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": ua, "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "sec-ch-ua": f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "Upgrade-Insecure-Requests": "1"})
        self._robots: dict[str, RobotsPolicy] = {}
        self._last = 0.0
        self.retries = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.s.close()

    def allowed(self, url: str) -> bool:
        key = robots_url(url)
        if key not in self._robots:
            try:
                r = self.s.get(key, timeout=15)
                self._robots[key] = RobotsPolicy(r.status_code, r.text)
            except requests.RequestException:
                self._robots[key] = RobotsPolicy(None)
            log.info("robots.txt %s → %s", key, self._robots[key].mode)
        return self._robots[key].allowed(url, settings.rpa_user_agent)

    def request(self, method: str, url: str, referer: str | None = None, json_api: bool = False, **kw) -> requests.Response:
        if not self.allowed(url):
            raise BrowserError(url, "robots.txt 비허용")

        def _go():
            wait = settings.request_interval_sec + random.uniform(0.2, 0.8) - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            headers = dict(kw.pop("headers", {}) or {})
            if referer:
                headers["Referer"] = referer
            if json_api:
                headers.update({"Accept": "application/json, text/plain, */*", "X-Requested-With": "XMLHttpRequest"})
                if referer:
                    headers["Origin"] = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
            r = self.s.request(method, url, headers=headers, timeout=settings.playwright_timeout_ms / 1000, **kw)
            self._last = time.monotonic()
            if r.status_code in (403, 429) or r.status_code >= 500:
                raise RuntimeError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r

        r, n = retry(_go, url, attempts=settings.rpa_retries + 1)
        self.retries += n
        log.info("요청 %s %s (%s) %d bytes", method, url[:120], r.status_code, len(r.content))
        return r

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)


def _strip(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(str(s or "")))).strip()


def _num(v) -> int:
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _ymd(s: str | None) -> str | None:
    """'20261109' / '2026.11.09 00:00:00' → '2026-11-09'."""
    m = re.search(r"(20\d{2})\D?(\d{2})\D?(\d{2})", s or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# ---------------------------------------------------------------- 여행사별 HTTP 수집
def hanatour(c, http: HttpSession, home_html: str, home: str) -> list[dict]:
    rows, seen = [], set()
    for url in c.discover(home_html):
        code = url.rstrip("/").rsplit("/", 1)[-1]
        api = f"https://gw.hanatour.com/dcr/promotions/plan/{code}?device=PC&siteCode=C00002S001&marketingCode="
        data = http.get(api, referer=url, json_api=True).json()

        def walk(o):
            if isinstance(o, dict):
                if "itemList" in o and isinstance(o["itemList"], list):
                    for it in o["itemList"]:
                        if not isinstance(it, dict) or not it.get("title") or not it.get("price"):
                            continue
                        pcode = it.get("productCodeInLink") or it.get("productCode")
                        link = it.get("linkTypeUrl_2") or it.get("linkTypeUrl_1") or ""
                        q = parse_qs(urlparse(link).query)
                        start = _ymd((q.get("strtDepDay") or [None])[0]) or _ymd(it.get("startAt"))
                        end = _ymd((q.get("endDepDay") or [None])[0]) or _ymd(it.get("endAt"))
                        key = (pcode, start)
                        if not pcode or key in seen:
                            continue
                        seen.add(key)
                        days = [d for d in it.get("travelDaysList") or [] if str(d).isdigit()]
                        price, org = _num(it["price"]), _num(it.get("orgPrice"))
                        if not price:
                            continue
                        rows.append({"code": f"HT{pcode}", "title": _strip(it["title"]), "price": str(price),
                                     "original_price": str(org) if org > price else None,
                                     "depart": start, "depart_end": end if end and end != start else None,
                                     "duration": f"{','.join(days)}일" if days else None,
                                     "link": urljoin("https://www.hanatour.com", link) if link else url})
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(data)
    return c.exclude(rows)


def modetour(c, http: HttpSession, home_html: str, home: str) -> list[dict]:
    rows = []
    for url in c.discover(home_html):
        page = http.get(url, referer=home)
        found = c.parse(page.text, url)  # __NEXT_DATA__ 파서 재사용
        if not found:
            log.info("[modetour] live 0건(구조 변경 추정): %s", url)
        rows += found
    return rows


def ybtour(c, http: HttpSession, home_html: str, home: str) -> list[dict]:
    rows, seen = [], set()
    for url in c.discover(home_html):
        page = http.get(url, referer=home).text
        for tno in dict.fromkeys(re.findall(r"templateNo\W{1,5}(\d{6,})", page)):
            data = http.post("https://pkg.ybtour.co.kr/promotion/soldOutTemplate.ajax", data={"templateNo": tno},
                             referer=url, json_api=True).json()
            for g in data.get("soldOutGoodsList") or []:
                code = g.get("goodsCd")
                if not code or code in seen or g.get("soldOutYn") == "Y":
                    continue
                seen.add(code)
                price, disc = _num(g.get("price")), _num(g.get("discPrice"))
                note = _strip(g.get("beneNote"))
                m = re.search(r"(\d{1,2}/\d{1,2}(?:\s*,\s*\d{1,2})*)", note)
                link = g.get("goodsLink") or url
                rows.append({"code": str(code), "title": _strip(str(g.get("showNm") or "").split("<BR>")[0].split("<br>")[0]),
                             "price": str(disc or price), "original_price": str(price) if disc and price > disc else None,
                             "depart": m.group(1).replace(" ", "") if m else None, "image": g.get("imgUrl"),
                             "link": urljoin(url, link)})
    return c.exclude(rows)


FETCHERS = {"hanatour": hanatour, "modetour": modetour, "ybtour": ybtour}

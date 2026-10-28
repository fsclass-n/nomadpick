"""여행사 수집기 공통 - Playwright 렌더링 HTML 을 selectors.json 규칙으로 파싱, live/sample/auto 모드."""
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from backend.app.config import settings

from . import sample_site
from .browser import BrowserError, HumanBrowser

log = logging.getLogger(__name__)
SELECTORS = json.loads((Path(__file__).resolve().parents[1] / "selectors.json").read_text(encoding="utf-8"))
FIELDS = ("code", "title", "link", "depart", "duration", "price", "original_price", "seats", "airline", "origin", "image")


@dataclass
class CollectResult:
    agency: str
    source: str = "live"
    raw: list[dict] = field(default_factory=list)
    retries: int = 0
    pages: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def select_value(item: Tag, selector: str) -> str | None:
    for alt in selector.split("|"):
        css, _, attr = alt.partition("@")
        el = item.select_one(css) if css else item
        if el is None:
            continue
        value = el.get(attr) if attr else el.get_text(" ", strip=True)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


class BaseCollector:
    agency: str = ""

    def __init__(self) -> None:
        self.conf = SELECTORS[self.agency]

    # ---------- 파싱 ----------
    def postprocess(self, row: dict, item: Tag) -> dict:
        """여행사별 보정이 필요하면 재정의."""
        return row

    def parse(self, html: str, page_url: str) -> list[dict]:
        sel = self.conf["selectors"]
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for item in soup.select(sel["item"]):
            row = {f: select_value(item, sel[f]) for f in FIELDS if f in sel}
            row["link"] = row.get("link") or page_url
            rows.append(self.postprocess(row, item))
        return self.exclude(rows)

    def exclude(self, rows: list[dict]) -> list[dict]:
        """패키지 상품이 아닌 항목(예: 왕복 항공권)은 수집 대상에서 제외하고, 상품코드 접두어로 도시 힌트를 붙인다."""
        words = self.conf.get("exclude_keywords", [])
        rows = [r for r in rows if not any(w in (r.get("title") or "") for w in words)]
        for r in rows:
            r["city_hint"] = next((c for p, c in self.conf.get("code_city", {}).items() if str(r.get("code") or "").startswith(p)), None)
        return rows

    def fallback_urls(self) -> list[str]:
        return [u for rule in self.conf["discover"] for u in rule["fallback"]]

    def discover(self, home_html: str) -> list[str]:
        """홈 화면에서 현재 진행 중인 특가 페이지 주소를 규칙(해외 특가·국내)별로 찾는다(기획전 번호가 바뀌어도 대응).

        규칙마다 찾지 못하면 그 규칙의 fallback 주소를 사용한다.
        """
        text = home_html.replace("\\u002F", "/").replace("&amp;", "&")
        urls: list[str] = []
        for rule in self.conf["discover"]:
            found: list[str] = []
            for m in re.finditer(rule["pattern"], text):
                url = rule.get("base", "") + m.group(1)
                if url not in found:
                    found.append(url)
                if len(found) >= rule.get("max", 1):
                    break
            urls += [u for u in found or rule["fallback"] if u not in urls]
        return urls

    # ---------- 수집 ----------
    async def collect_live(self, browser: HumanBrowser) -> CollectResult:
        """여행사 1곳을 전용 컨텍스트로 수집하고, 끝나면 컨텍스트를 닫아 메모리를 반환한다."""
        result = CollectResult(agency=self.agency)
        async with browser.session() as s:
            await self._collect_live(result, s)
        return result

    async def _collect_live(self, result: CollectResult, browser) -> None:
        home = self.conf["home"]
        if not await browser.allowed(home):
            result.messages.append(f"robots.txt 비허용/확인 불가: {home}")
            return
        try:
            home_page = await browser.visit(home)
            result.retries += home_page.retries
            urls = self.discover(home_page.html)
        except BrowserError as e:
            result.retries += e.retries
            result.messages.append(f"홈 접속 실패: {e}")
            if "Timeout" in str(e):  # 홈조차 응답이 없으면(차단·네트워크) 기획전도 실패 → 시간·메모리 낭비 없이 건너뜀
                result.messages.append("홈 응답 없음 - 해당 여행사 건너뜀")
                return
            urls = self.fallback_urls()
        for url in urls:
            if not await browser.allowed(url):
                result.messages.append(f"robots.txt 비허용: {url}")
                continue
            try:
                page = await browser.visit(url, referer=home, wait_selector=self.conf.get("wait_for"))
                result.retries += page.retries
                rows = self.parse(page.html, page.url)
                result.raw.extend(rows)
                result.pages.append(page.url)
                if not rows:
                    result.messages.append(f"live 0건(구조 변경 추정): {url}")
            except BrowserError as e:
                result.retries += e.retries
                result.messages.append(f"페이지 실패: {e}")

    def collect_sample(self, result: CollectResult, at: datetime) -> None:
        result.source = "sample"
        result.raw = sample_site.parse_sample(self.agency, at)

    def collect(self, at: datetime, mode: str | None = None, live: CollectResult | None = None) -> CollectResult:
        """live: run.collect_live_all() 이 미리 수집한 결과 (None 이면 브라우저 시작 실패)."""
        mode = mode or settings.rpa_source_mode
        result = CollectResult(agency=self.agency)
        if mode in ("live", "auto") and live is not None:
            result = live
        elif mode in ("live", "auto"):
            result.messages.append("브라우저 시작 실패")
        if mode == "sample" or (mode == "auto" and not result.raw):
            if mode == "auto":
                result.messages.append("sample 페이지로 대체")
            self.collect_sample(result, at)
        log.info("[%s] %s %d건 %s", self.agency, result.source, len(result.raw), " / ".join(result.messages))
        return result

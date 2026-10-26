"""Playwright 기반 '사람처럼' 동작하는 수집 브라우저.

여행사 특가 목록은 JavaScript 로 렌더링되고(하나투어·노랑풍선·모두투어), 모두투어는 봇형 HTTP 요청을
Access Denied 로 차단한다. 일반 사용자의 Chrome 과 같은 조건으로 페이지를 열어 렌더링된 HTML 을 얻는다.

사람과 같은 접근 방식
- 실제 Chrome 과 같은 User-Agent · sec-ch-ua 헤더 · 한국어 로케일 · Asia/Seoul 시간대 · 일반 해상도
- 자동화 흔적 제거: navigator.webdriver, AutomationControlled 플래그, plugins/languages/chrome 객체
- 홈 화면 먼저 방문(쿠키·Referer 형성) → 특가 페이지 이동, 마우스 이동·단계별 스크롤·불규칙한 대기
- 수집 예의: robots.txt 확인(RFC 9309), 페이지 간 2초 이상 간격, 실패 시 3회 재시도(2·4·8초)
"""
import logging
import random
import time
from dataclasses import dataclass

from backend.app.config import settings

from .robots import RobotsPolicy, robots_url

log = logging.getLogger(__name__)

VIEWPORTS = [(1920, 1080), (1536, 864), (1440, 900), (1366, 768), (1600, 900)]
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
window.chrome = window.chrome || {runtime: {}, app: {}, csi: () => {}, loadTimes: () => {}};
const _query = window.navigator.permissions && window.navigator.permissions.query;
if (_query) {
  window.navigator.permissions.query = (p) =>
    p && p.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : _query(p);
}
"""
BLOCK_TYPES = {"image", "media", "font"}


class BrowserError(Exception):
    def __init__(self, url: str, reason: str, retries: int = 0):
        super().__init__(f"{url} - {reason}")
        self.retries = retries


@dataclass
class PageResult:
    url: str
    status: int
    html: str
    retries: int = 0


def retry(fn, url: str, attempts: int = 4, sleep=time.sleep):
    """최초 1회 + 재시도 3회 (2·4·8초 지수 백오프). (결과, 재시도 횟수) 반환."""
    last = ""
    for attempt in range(attempts):
        try:
            return fn(), attempt
        except Exception as e:  # Playwright TimeoutError, 네트워크 오류, 차단 응답
            last = str(e).splitlines()[0][:200]
            if attempt < attempts - 1:
                log.warning("요청 실패(%s) %d/%d 재시도: %s", url, attempt + 1, attempts - 1, last)
                sleep(2 ** (attempt + 1))
    raise BrowserError(url, last, retries=attempts - 1)


def human_pause(lo: float = 0.6, hi: float = 1.8) -> None:
    time.sleep(random.uniform(lo, hi))


class HumanBrowser:
    """with HumanBrowser() as b: b.visit(url) - 한 번의 수집 실행 동안 같은 브라우저·쿠키를 사용한다."""

    def __init__(self) -> None:
        self._pw = self._browser = self._ctx = self._page = None
        self._robots: dict[str, RobotsPolicy] = {}
        self._last_visit = 0.0

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        launch = {"headless": settings.playwright_headless, "args": [
            "--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage",
            "--lang=ko-KR"]}
        if settings.playwright_channel:
            launch["channel"] = settings.playwright_channel
        self._browser = self._pw.chromium.launch(**launch)
        w, h = random.choice(VIEWPORTS)
        major = settings.rpa_user_agent.split("Chrome/")[-1].split(".")[0] if "Chrome/" in settings.rpa_user_agent else "131"
        self._ctx = self._browser.new_context(
            user_agent=settings.rpa_user_agent, locale="ko-KR", timezone_id="Asia/Seoul",
            viewport={"width": w, "height": h}, screen={"width": w, "height": h}, device_scale_factor=1,
            color_scheme="light", java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "sec-ch-ua": f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            })
        self._ctx.add_init_script(STEALTH_JS)
        if settings.playwright_block_media:  # 이미지·영상·폰트는 받지 않아 메모리·트래픽 절약
            self._ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in BLOCK_TYPES else r.continue_())
        self._ctx.set_default_navigation_timeout(settings.playwright_timeout_ms)
        self._page = self._ctx.new_page()
        return self

    def __exit__(self, *exc):
        for obj in (self._ctx, self._browser):
            try:
                obj and obj.close()
            except Exception:
                pass
        if self._pw:
            self._pw.stop()

    # ---------- 예의 ----------
    def robots(self, url: str) -> RobotsPolicy:
        key = robots_url(url)
        if key not in self._robots:
            try:
                r = self._ctx.request.get(key, timeout=15000)
                self._robots[key] = RobotsPolicy(r.status, r.text())
            except Exception:
                self._robots[key] = RobotsPolicy(None)
            log.info("robots.txt %s → %s", key, self._robots[key].mode)
        return self._robots[key]

    def allowed(self, url: str) -> bool:
        return self.robots(url).allowed(url, settings.rpa_user_agent)

    def _respect_interval(self) -> None:
        wait = settings.request_interval_sec + random.uniform(0.3, 1.2) - (time.monotonic() - self._last_visit)
        if wait > 0:
            time.sleep(wait)

    # ---------- 사람처럼 보기 ----------
    def _behave(self) -> None:
        page = self._page
        vw = page.viewport_size or {"width": 1366, "height": 768}
        for _ in range(random.randint(2, 4)):
            page.mouse.move(random.randint(50, vw["width"] - 50), random.randint(80, vw["height"] - 80),
                            steps=random.randint(8, 20))
            human_pause(0.2, 0.6)
        last_height = 0
        for _ in range(random.randint(8, 12)):  # 지연 로딩 목록이 모두 나타나도록 단계별 스크롤
            page.mouse.wheel(0, random.randint(450, 900))
            human_pause(0.4, 1.1)
            height = page.evaluate("document.body.scrollHeight")
            if height == last_height and page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight - 10"):
                break
            last_height = height
        human_pause(0.8, 1.6)

    def visit(self, url: str, referer: str | None = None, wait_selector: str | None = None) -> PageResult:
        def _go():
            self._respect_interval()
            resp = self._page.goto(url, wait_until="domcontentloaded", referer=referer)
            self._last_visit = time.monotonic()
            status = resp.status if resp else 0
            if status in (403, 429) or status >= 500:
                raise RuntimeError(f"HTTP {status}")
            try:
                self._page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            if wait_selector:
                try:
                    self._page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass
            self._behave()
            return PageResult(url=self._page.url, status=status, html=self._page.content())

        result, retries = retry(_go, url)
        result.retries = retries
        log.info("방문 %s (%s) %d bytes", url, result.status, len(result.html))
        return result

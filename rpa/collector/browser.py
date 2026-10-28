"""Playwright(Async API) 기반 '사람처럼' 동작하는 저메모리 수집 브라우저.

Render 무료 인스턴스(RAM 512MB)에서도 OOM 없이 동작하도록
- 크롬 메모리 최적화·크래시 방지 실행 옵션(--no-sandbox, --disable-dev-shm-usage, --disable-gpu, 프로세스 수 제한 등)
- 이미지·CSS·폰트·미디어 등 불필요한 리소스 차단(page.route)
- 여행사마다 컨텍스트를 새로 만들고 작업 후 즉시 종료, 브라우저·Playwright 는 try/finally 로 반드시 종료
사람과 같은 접근: 실제 Chrome UA·sec-ch-ua·ko-KR·Asia/Seoul, 자동화 흔적 제거, 홈 → 특가 페이지, 단계별 스크롤
수집 예의: robots.txt(RFC 9309), 페이지 간 2초 이상, 3회 재시도(2·4·8초)
"""
import asyncio
import logging
import random
import time
from dataclasses import dataclass

from backend.app.config import settings

from .robots import RobotsPolicy, robots_url

log = logging.getLogger(__name__)

# 저메모리·크래시 방지 실행 옵션
LAUNCH_ARGS = [
    "--no-sandbox",                       # 컨테이너(root) 환경 필수
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",            # /dev/shm(64MB) 대신 /tmp 사용 → 공유 메모리 부족 크래시 방지
    "--disable-gpu",                      # GPU 프로세스 미사용
    "--no-zygote",                        # 보조 프로세스 감소
    "--renderer-process-limit=1",         # 렌더러 프로세스 1개로 제한
    "--disable-features=site-per-process,Translate,BackForwardCache,MediaRouter",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--disable-default-apps",
    "--no-first-run",
    "--mute-audio",
    "--blink-settings=imagesEnabled=false",
    "--js-flags=--max-old-space-size=256",
    "--disable-blink-features=AutomationControlled",
    "--lang=ko-KR",
]
VIEWPORTS = [(1366, 768), (1440, 900), (1536, 864)]
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
window.chrome = window.chrome || {runtime: {}, app: {}};
"""


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
    """(동기) 최초 1회 + 재시도 3회 (2·4·8초). (결과, 재시도 횟수) 반환 - 테스트·동기 호출용."""
    last = ""
    for attempt in range(attempts):
        try:
            return fn(), attempt
        except Exception as e:
            last = str(e).splitlines()[0][:200]
            if attempt < attempts - 1:
                sleep(2 ** (attempt + 1))
    raise BrowserError(url, last, retries=attempts - 1)


async def aretry(coro_fn, url: str, attempts: int | None = None):
    """(비동기) 최초 1회 + 재시도 RPA_RETRIES 회 (2·4·8초)."""
    attempts = attempts or settings.rpa_retries + 1
    last = ""
    for attempt in range(attempts):
        try:
            return await coro_fn(), attempt
        except Exception as e:
            last = str(e).splitlines()[0][:200]
            if attempt < attempts - 1:
                log.warning("요청 실패(%s) %d/%d 재시도: %s", url, attempt + 1, attempts - 1, last)
                await asyncio.sleep(2 ** (attempt + 1))
    raise BrowserError(url, last, retries=attempts - 1)


class HumanBrowser:
    """async with HumanBrowser() as b:  async with b.session() as s: await s.visit(url)"""

    def __init__(self) -> None:
        self._pw = self._browser = None
        self._robots: dict[str, RobotsPolicy] = {}

    async def __aenter__(self):
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        try:
            launch = {"headless": settings.playwright_headless, "args": LAUNCH_ARGS}
            if settings.playwright_channel:
                launch["channel"] = settings.playwright_channel
            self._browser = await self._pw.chromium.launch(**launch)
        except Exception:
            await self._pw.stop()
            raise
        return self

    async def __aexit__(self, *exc):
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()
            self._browser = self._pw = None

    def session(self) -> "Session":
        return Session(self)


class Session:
    """여행사 1곳 수집용 컨텍스트 - 종료 시 컨텍스트·페이지를 모두 닫아 메모리를 돌려준다."""

    def __init__(self, browser: HumanBrowser):
        self.b = browser
        self.ctx = self.page = None
        self._last = 0.0

    async def __aenter__(self):
        w, h = random.choice(VIEWPORTS)
        ua = settings.rpa_user_agent
        major = ua.split("Chrome/")[-1].split(".")[0] if "Chrome/" in ua else "131"
        self.ctx = await self.b._browser.new_context(
            user_agent=ua, locale="ko-KR", timezone_id="Asia/Seoul", viewport={"width": w, "height": h},
            extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
                                "sec-ch-ua": f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not_A Brand";v="24"',
                                "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"'})
        try:
            await self.ctx.add_init_script(STEALTH_JS)
            if settings.playwright_block_media:
                await self.ctx.route("**/*", self._block)
            self.ctx.set_default_navigation_timeout(settings.playwright_timeout_ms)
            self.page = await self.ctx.new_page()
        except Exception:
            await self.ctx.close()
            raise
        return self

    async def __aexit__(self, *exc):
        try:
            if self.page:
                await self.page.close()
        finally:
            if self.ctx:
                await self.ctx.close()
            self.ctx = self.page = None

    @staticmethod
    async def _block(route):
        """이미지·CSS·폰트·미디어 등 HTML 파싱에 필요 없는 리소스는 받지 않는다."""
        if route.request.resource_type in settings.playwright_block_types:
            await route.abort()
        else:
            await route.continue_()

    async def robots(self, url: str) -> RobotsPolicy:
        key = robots_url(url)
        if key not in self.b._robots:
            try:
                r = await self.ctx.request.get(key, timeout=15000)
                self.b._robots[key] = RobotsPolicy(r.status, await r.text())
            except Exception:
                self.b._robots[key] = RobotsPolicy(None)
            log.info("robots.txt %s → %s", key, self.b._robots[key].mode)
        return self.b._robots[key]

    async def allowed(self, url: str) -> bool:
        return (await self.robots(url)).allowed(url, settings.rpa_user_agent)

    async def _behave(self):
        try:
            await self._scroll()
        except Exception as e:  # 스크롤 중 페이지 자체 리다이렉트(JS 이동) → 이동한 페이지 그대로 사용
            log.info("스크롤 중단(페이지 이동): %s", str(e).splitlines()[0][:80])
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

    async def _scroll(self):
        p = self.page
        vw = p.viewport_size or {"width": 1366, "height": 768}
        for _ in range(random.randint(2, 3)):
            await p.mouse.move(random.randint(50, vw["width"] - 50), random.randint(80, vw["height"] - 80), steps=12)
            await asyncio.sleep(random.uniform(0.2, 0.5))
        last = 0
        for _ in range(random.randint(8, 12)):  # 지연 로딩 목록이 나타나도록 단계별 스크롤
            await p.mouse.wheel(0, random.randint(450, 900))
            await asyncio.sleep(random.uniform(0.4, 1.0))
            height = await p.evaluate("document.body.scrollHeight")
            if height == last and await p.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight - 10"):
                break
            last = height

    async def visit(self, url: str, referer: str | None = None, wait_selector: str | None = None) -> PageResult:
        async def _go():
            wait = settings.request_interval_sec + random.uniform(0.3, 1.0) - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            resp = await self.page.goto(url, wait_until="domcontentloaded", referer=referer)
            self._last = time.monotonic()
            status = resp.status if resp else 0
            if status in (403, 429) or status >= 500:
                raise RuntimeError(f"HTTP {status}")
            try:
                await self.page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            if wait_selector:
                try:
                    await self.page.wait_for_selector(wait_selector, timeout=10000, state="attached")
                except Exception:
                    pass
            await self._behave()
            return PageResult(url=self.page.url, status=status, html=await self.page.content())

        result, retries = await aretry(_go, url)
        result.retries = retries
        log.info("방문 %s (%s) %d bytes", url, result.status, len(result.html))
        return result

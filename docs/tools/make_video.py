"""10분 발표·시연 영상(MP4) 자동 제작.

    .venv\\Scripts\\python.exe docs\\tools\\make_video.py [--base http://127.0.0.1:8000] [--target-mb 85]

1) docs/md/07_발표영상_대본.md 의 장면(#### ⏱️)별 나레이션(>)을 읽어 Edge 한국어 음성(ko-KR-InJoonNeural)으로 TTS
2) 발표자료 슬라이드를 1920×1080 PNG 로 내보내 PPT 파트 영상 생성 (PowerPoint COM, Windows)
3) 웹 시연은 Playwright 로 대본 동선(일반 회원 → 관리자)을 자동 조작하며 녹화 (커서 하이라이트 표시)
4) FFmpeg(imageio-ffmpeg)로 장면별 음성과 영상을 맞춰 합치고 목표 용량(기본 85MB)으로 2-pass 압축
결과: docs/video/nomadpick_demo.mp4
"""
import argparse
import asyncio
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SCRIPT_MD = ROOT / "docs" / "md" / "07_발표영상_대본.md"
PPTX = ROOT / "docs" / "프로젝트_발표자료.pptx"
WORK = ROOT / "docs" / "tools" / "out" / "video"
OUT = ROOT / "docs" / "video" / "nomadpick_demo.mp4"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE, RATE = "ko-KR-InJoonNeural", "-3%"
W, H, FPS = 1920, 1080, 30
VIEW = (1536, 864)          # 녹화 화면(125% 확대 효과) → 1920×1080 으로 확대
PAD = 0.7                   # 장면 끝 여유(초)

# 장면 번호 → 화면 (대본의 #### ⏱️ 순서와 동일, 총 23장면)
SLIDE_SCENES = {0: [1], 1: [2], 2: [3], 3: [4], 4: [5], 5: [6], 6: [7, 8], 7: [9], 8: [10, 11], 9: [12], 21: [14], 22: [15]}
DEMO_SCENES = list(range(10, 21))


def ff(*args):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], check=True)


def duration(path: Path) -> float:
    err = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


# ---------------------------------------------------------------- 1. 대본·TTS
def parse_scenes() -> list[dict]:
    scenes, cur = [], None
    for line in SCRIPT_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("#### ⏱️"):
            cur = {"title": line[8:].strip(), "text": []}
            scenes.append(cur)
        elif cur is not None and line.strip().startswith(">"):
            cur["text"].append(line.strip()[1:].strip().replace("**", ""))
    for s in scenes:
        s["text"] = " ".join(s["text"])
    if len(scenes) != 23:
        raise SystemExit(f"대본 장면 수가 23개가 아닙니다: {len(scenes)}")
    return scenes


def make_tts(scenes: list[dict]) -> None:
    import edge_tts

    async def run():
        for i, s in enumerate(scenes):
            key = hashlib.md5((VOICE + RATE + s["text"]).encode()).hexdigest()[:10]
            s["audio"] = WORK / f"scene_{i:02d}_{key}.mp3"
            if not s["audio"].exists():
                await edge_tts.Communicate(s["text"], VOICE, rate=RATE).save(str(s["audio"]))
            s["dur"] = duration(s["audio"]) + PAD
    asyncio.run(run())


# ---------------------------------------------------------------- 2. 슬라이드
def export_slides() -> None:
    if all((WORK / f"slide_{i:02d}.png").exists() for i in range(1, 16)):
        return
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    pres = ppt.Presentations.Open(str(PPTX), WithWindow=False)
    for i in range(1, pres.Slides.Count + 1):
        pres.Slides(i).Export(str(WORK / f"slide_{i:02d}.png"), "PNG", W, H)
    pres.Close()


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", FPS,
       "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k"]


def slide_segment(i: int, scene: dict) -> Path:
    out = WORK / f"seg_{i:02d}.mp4"
    slides = SLIDE_SCENES[i]
    part = scene["dur"] / len(slides)
    inputs = []
    for n in slides:
        inputs += ["-loop", "1", "-t", f"{part:.3f}", "-framerate", FPS, "-i", WORK / f"slide_{n:02d}.png"]
    vf = "".join(f"[{k}:v]scale={W}:{H},setsar=1[v{k}];" for k in range(len(slides)))
    vf += "".join(f"[v{k}]" for k in range(len(slides))) + f"concat=n={len(slides)}:v=1:a=0[v];"
    vf += f"[{len(slides)}:a]aresample=44100,apad,atrim=0:{scene['dur']:.3f}[a]"
    ff(*inputs, "-i", scene["audio"], "-filter_complex", vf, "-map", "[v]", "-map", "[a]", *ENC, "-t", f"{scene['dur']:.3f}", out)
    return out


# ---------------------------------------------------------------- 3. 웹 시연 녹화
CURSOR_JS = """
(() => {
  const init = () => {
    if (document.getElementById('__np_cursor')) return;
    const c = document.createElement('div');
    c.id = '__np_cursor';
    c.style.cssText = 'position:fixed;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;' +
      'border:3px solid rgba(255,170,0,.95);background:rgba(255,200,0,.28);box-shadow:0 0 6px rgba(0,0,0,.35);' +
      'z-index:2147483647;pointer-events:none;transition:transform .12s';
    const p = JSON.parse(sessionStorage.getItem('__np_pos') || '[760,430]');
    c.style.left = p[0] + 'px'; c.style.top = p[1] + 'px';
    document.body.appendChild(c);
    document.addEventListener('mousemove', e => {
      c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      sessionStorage.setItem('__np_pos', JSON.stringify([e.clientX, e.clientY]));
    }, true);
    document.addEventListener('mousedown', () => { c.style.transform = 'scale(.7)'; }, true);
    document.addEventListener('mouseup', () => { c.style.transform = 'scale(1)'; }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
"""


class Demo:
    def __init__(self, page, base: str):
        self.p, self.base = page, base.rstrip("/")

    def wait(self, s: float):
        self.p.wait_for_timeout(int(s * 1000))

    def move(self, target, dx: float = 0.5, dy: float = 0.5):
        loc = self.p.locator(target).first if isinstance(target, str) else target
        loc.scroll_into_view_if_needed(timeout=5000)
        b = loc.bounding_box()
        x, y = b["x"] + b["width"] * dx, b["y"] + b["height"] * dy
        self.p.mouse.move(x, y, steps=28)
        self.wait(0.35)
        return x, y

    def click(self, target, after: float = 0.6):
        x, y = self.move(target)
        self.p.mouse.click(x, y)
        self.wait(after)

    def type(self, target, text: str):
        self.click(target, 0.2)
        self.p.locator(target).first.press_sequentially(text, delay=85)
        self.wait(0.3)

    def select(self, target, value: str):
        self.move(target)
        self.p.select_option(target, value)
        self.wait(0.8)

    def scroll(self, dy: int, steps: int = 6):
        for _ in range(steps):
            self.p.mouse.wheel(0, dy / steps)
            self.wait(0.18)

    def goto(self, path: str):
        self.p.goto(self.base + path, wait_until="domcontentloaded")
        self.p.wait_for_load_state("networkidle", timeout=15000)


def demo_actions(d: Demo, ctx: dict):
    """장면 번호 → 동작. 각 동작은 장면 길이(나레이션) 안에서 실행되고 남는 시간은 대기한다."""
    s = settings_mod()

    def main_page():
        d.goto("/index.html")
        d.p.wait_for_selector("#cards .np-card", timeout=20000)
        d.wait(1.0)
        for sel in ("#statTotal", "#statUpdated"):
            d.move(sel)
            d.wait(0.8)
        d.click("#regionChips label:text-is('동남아')", 1.2)
        d.select("select[name=price_max]", "1000000")
        d.select("#sortSelect", "price")
        d.type("input[name=q]", "다낭")
        d.p.keyboard.press("Enter")
        d.wait(1.5)
        d.move("#cards .np-card")
        d.wait(1.2)
        d.p.fill("input[name=q]", "")
        d.p.keyboard.press("Enter")
        d.wait(1.0)
        d.scroll(700)

    def signup():
        d.scroll(-2000, 4)
        d.click("a.btn:has-text('회원가입')", 1.0)
        d.type("#name", "김길동")
        d.type("#email", ctx["email"])
        d.type("#password", ctx["password"])
        d.type("#password2", ctx["password"])
        d.click("#submitBtn", 0.5)
        d.p.wait_for_url("**/preferences.html*", timeout=20000)
        d.p.wait_for_selector("#regions label", timeout=10000)
        d.move("#welcome")
        for label in ("동남아", "일본"):
            d.click(f"#regions label:text-is('{label}')", 0.4)
        for sel, val in (("#budgetMin", 300000), ("#budgetMax", 1000000)):
            d.move(sel)
            d.p.eval_on_selector(sel, "(el, v) => { el.value = v; el.dispatchEvent(new Event('input')); }", val)
            d.wait(0.5)
        d.click("#months label:text-is('12월')", 0.4)
        d.select("#nightsMin", "3")
        d.select("#nightsMax", "4")
        d.click("#themes label:text-is('휴양')", 0.4)
        d.click("#companions label:text-is('친구')", 0.4)
        d.click("#saveBtn", 0.3)
        d.p.wait_for_url("**/recommend.html", timeout=20000)

    def recommend():
        d.p.wait_for_selector("#list .np-panel", timeout=20000)
        d.move("#prefSummary")
        d.wait(1.0)
        reasons = d.p.locator("#list .np-reason")
        for k in range(min(3, reasons.count())):
            d.move(reasons.nth(k))
            d.wait(0.7)
        d.move("#list .np-score")
        d.wait(1.0)
        d.scroll(1800, 12)
        d.wait(0.8)
        d.scroll(-2400, 8)
        with d.p.expect_download(timeout=20000):
            d.click("#excelBtn", 0.3)
        d.wait(1.5)

    def product():
        d.click("#list .np-panel a.fs-5", 0.5)
        d.p.wait_for_selector("#detail h1", timeout=20000)
        d.wait(2.5)
        d.goto(f"/product.html?id={ctx['domestic_id']}")
        d.p.wait_for_selector("#detail h1", timeout=20000)
        d.wait(1.0)
        d.move("#detail .np-price")
        d.wait(1.0)
        for dx in (0.25, 0.5, 0.75):
            d.move("#priceChart", dx, 0.5)
            d.wait(0.6)
        d.move("#flights")
        d.wait(1.5)
        d.click("#favBtn", 1.2)
        d.move("a:has-text('예약하러 가기')")

    def mypage():
        d.click("nav a.nav-link:has-text('마이페이지')", 0.5)
        d.p.wait_for_selector("#favorites .np-panel", timeout=20000)
        d.move("#favorites .badge")
        d.wait(1.2)
        d.move("#npNav ul.navbar-nav")
        d.wait(1.0)
        d.goto("/admin.html")
        d.wait(0.8)
        d.move("main .alert")

    def admin_login():
        d.click("a.dropdown-toggle", 0.6)
        d.click("#np-logout", 0.8)
        d.p.wait_for_url("**/index.html", timeout=15000)
        d.click("nav a.nav-link:text-is('로그인')", 0.8)
        d.type("#email", s.admin_email)
        d.type("#password", s.admin_password)
        d.click("#submitBtn", 0.3)
        d.p.wait_for_url("**/admin.html", timeout=20000)
        d.p.wait_for_selector("#agencyRows tr", timeout=20000)
        d.move("nav a.nav-link:has-text('수집 모니터링')")

    def kpi():
        for sel in ("#kRuns", "#kCollected", "#kSuccess", "#kFail"):
            d.move(sel)
            d.wait(1.6)

    def agencies():
        rows = d.p.locator("#agencyRows tr")
        for k in range(rows.count()):
            d.move(rows.nth(k), 0.4)
            d.wait(1.0)
        for dx in (0.3, 0.6, 0.85):
            d.move("#dailyChart", dx, 0.55)
            d.wait(0.8)

    def logs():
        d.move("#logRows tr")
        rows = d.p.locator("#logRows tr")
        for k in range(min(6, rows.count())):
            d.move(rows.nth(k), 0.6)
            d.wait(0.9)
        d.scroll(400, 5)

    def manual_run():
        d.scroll(-3000, 5)
        d.click("[data-run=report]", 1.5)

    def report():
        d.move("#reports")
        d.wait(1.0)
        if d.p.locator("[data-xlsx]").count():
            with d.p.expect_download(timeout=20000):
                d.click("[data-xlsx]", 0.3)
            d.move("[data-html]")

    return {10: main_page, 11: signup, 12: recommend, 13: product, 14: mypage,
            15: admin_login, 16: kpi, 17: agencies, 18: logs, 19: manual_run, 20: report}


def settings_mod():
    from backend.app.config import settings
    return settings


def record_demo(scenes: list[dict], base: str) -> tuple[Path, list[float]]:
    import requests
    from playwright.sync_api import sync_playwright

    api = base.rstrip("/") + "/api/v1"
    items = requests.get(f"{api}/products", params={"region": "국내", "sort": "depart", "size": 50}, timeout=60).json()["items"]
    domestic = next((i["id"] for i in items if requests.get(f"{api}/products/{i['id']}", timeout=30).json().get("flights")),
                    items[0]["id"] if items else 1)
    ctx = {"email": f"nomad.demo{int(time.time()) % 100000}@example.com", "password": "Demo!2026a", "domestic_id": domestic}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, locale="ko-KR",
                                      timezone_id="Asia/Seoul", record_video_dir=str(WORK),
                                      record_video_size={"width": VIEW[0], "height": VIEW[1]}, accept_downloads=True)
        context.add_init_script(CURSOR_JS)
        page = context.new_page()
        t0 = time.monotonic()
        d = Demo(page, base)
        actions = demo_actions(d, ctx)
        offsets = []
        for i in DEMO_SCENES:
            start = time.monotonic() - t0
            offsets.append(start)
            try:
                actions[i]()
            except Exception as e:  # 동작 하나가 실패해도 녹화는 이어간다
                print(f"  [경고] 장면 {i} 동작 실패: {str(e).splitlines()[0][:120]}")
            remain = scenes[i]["dur"] - (time.monotonic() - t0 - start)
            if remain > 0:
                d.wait(remain)
            print(f"  장면 {i:02d} {scenes[i]['title'][:28]} → {time.monotonic() - t0 - start:.1f}s")
        offsets.append(time.monotonic() - t0)
        video = Path(page.video.path())
        context.close()
        browser.close()
    return video, offsets


def demo_segment(video: Path, offsets: list[float], scenes: list[dict]) -> Path:
    out = WORK / "seg_demo.mp4"
    start, total = offsets[0], offsets[-1] - offsets[0]
    inputs, af = ["-ss", f"{start:.3f}", "-t", f"{total:.3f}", "-i", video], ""
    for k, i in enumerate(DEMO_SCENES):
        inputs += ["-i", scenes[i]["audio"]]
        seg = offsets[k + 1] - offsets[k]
        af += f"[{k + 1}:a]aresample=44100,apad,atrim=0:{seg:.3f},asetpts=N/SR/TB[a{k}];"
    af += "".join(f"[a{k}]" for k in range(len(DEMO_SCENES))) + f"concat=n={len(DEMO_SCENES)}:v=0:a=1[a];"
    af += f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS}[v]"
    ff(*inputs, "-filter_complex", af, "-map", "[v]", "-map", "[a]", *ENC, "-t", f"{total:.3f}", out)
    return out


# ---------------------------------------------------------------- 4. 합치기·압축
def assemble(segments: list[Path], target_mb: float) -> None:
    listing = WORK / "concat.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    full = WORK / "full.mp4"
    ff("-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", full)
    sec = duration(full)
    v_kbps = int(target_mb * 8 * 1024 / sec * 0.97 - 128)
    print(f"전체 {sec / 60:.1f}분 → 영상 {v_kbps}kbps 로 압축")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    log = WORK / "pass"
    common = ["-i", full, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{v_kbps}k", "-pix_fmt", "yuv420p", "-passlogfile", log]
    ff(*common, "-pass", "1", "-an", "-f", "mp4", "NUL" if sys.platform == "win32" else "/dev/null")
    ff(*common, "-pass", "2", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", OUT)
    print(f"완료: {OUT} ({OUT.stat().st_size / 1024 / 1024:.1f}MB, {duration(OUT) / 60:.1f}분)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="시연할 서비스 주소")
    ap.add_argument("--target-mb", type=float, default=85.0)
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)

    scenes = parse_scenes()
    make_tts(scenes)
    print(f"나레이션 {len(scenes)}장면, 합계 {sum(s['dur'] for s in scenes) / 60:.1f}분")
    export_slides()
    print("웹 시연 녹화 중 ...")
    video, offsets = record_demo(scenes, args.base)
    segs = {i: slide_segment(i, scenes[i]) for i in SLIDE_SCENES}
    demo = demo_segment(video, offsets, scenes)
    order = [segs[i] for i in range(10)] + [demo] + [segs[21], segs[22]]
    assemble(order, args.target_mb)


if __name__ == "__main__":
    main()

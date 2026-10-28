"""반응형 화면 목업 - Apple 공식 기기 프레임(MacBook Pro M5 14 · iPhone 17 Pro)에 실제 서비스 화면을 넣은 PNG.

    .venv\\Scripts\\python.exe docs\\tools\\make_mockups.py [--base http://127.0.0.1:8000]

- 기기 프레임: Apple Design Resources > Product Bezels (https://developer.apple.com/design/resources/)
  최초 실행 시 dmg 를 내려받아 7-Zip 으로 풀어 docs/tools/out/bezels 에 둔다 (저장소에는 넣지 않음, 7-Zip 필요)
  Apple 가이드라인에 따라 프레임은 변형(기울이기·왜곡)하지 않고 크기·배치·색상만 바꿔 장면마다 다른 구도를 만든다.
- 화면: MacBook 1512×982 @2x(=3024×1964), iPhone 402×874 @3x(=1206×2622) 로 실제 서비스를 캡처
결과: docs/md/images/mockup_{index,recommend,product,admin}.png
"""
import argparse
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "md" / "images"
BEZELS = ROOT / "docs" / "tools" / "out" / "bezels"
CDN = "https://devimages-cdn.apple.com/design/resources/download/"
MAC = {"silver": "Bezel-MacBook-Pro-M5/PNG/MacBook Pro M5 14-inch Silver.png",
       "black": "Bezel-MacBook-Pro-M5/PNG/MacBook Pro M5 14-inch Space Black.png"}
PHONE = {c: f"Bezel-iPhone-17/PNG/iPhone 17 Pro/iPhone 17 Pro - {name} - Portrait.png"
         for c, name in (("silver", "Silver"), ("orange", "Cosmic Orange"), ("blue", "Deep Blue"))}
DESK, MOBILE = ((1512, 982), 2), ((402, 874), 3)
PAGES = [("index", "/index.html", None), ("recommend", "/recommend.html", "demo"),
         ("product", "/product.html?id={pid}", "demo"), ("admin", "/admin.html", "admin")]

# 장면별 구도: (기기, 색상, 화면 키, x, y, 높이) - 캔버스 좌표, 뒤에 있는 기기부터
LAYOUTS = {
    "index": [("mac", "silver", "desk", 0, 0, 2540), ("phone", "silver", "mobile", 3200, 760, 1950)],
    "recommend": [("mac", "black", "desk", 1000, 0, 2540), ("phone", "orange", "mobile", 120, 760, 1950)],
    "product": [("mac", "silver", "desk", 0, 330, 2160), ("phone", "blue", "mobile_scroll", 2850, 520, 2050),
                ("phone", "orange", "mobile", 3800, 200, 2300)],
    "admin": [("mac", "black", "desk", 700, 0, 2540), ("phone", "silver", "mobile", 0, 1180, 1500)],
}


# ---------------------------------------------------------------- 프레임 준비
def ensure_bezels() -> None:
    if all((BEZELS / p).is_file() for p in [*MAC.values(), *PHONE.values()]):
        return
    seven = shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
    if not Path(seven).is_file():
        raise SystemExit("7-Zip 이 필요합니다: winget install 7zip.7zip")
    BEZELS.mkdir(parents=True, exist_ok=True)
    for name in ("Bezel-MacBook-Pro-M5", "Bezel-iPhone-17"):
        dmg = BEZELS / f"{name}.dmg"
        if not dmg.exists():
            print("내려받기", dmg.name)
            with requests.get(CDN + dmg.name, stream=True, timeout=900) as r:
                r.raise_for_status()
                with open(dmg, "wb") as f:
                    shutil.copyfileobj(r.raw, f)
        subprocess.run([seven, "x", "-y", f"-o{BEZELS}", str(dmg), "*.png", "-r"], check=True, capture_output=True)


def screen_mask(bezel: Image.Image) -> Image.Image:
    """프레임의 투명한 화면 영역(중앙에서 이어진 투명 픽셀) 마스크. 다이내믹 아일랜드·노치는 프레임이 덮는다."""
    alpha = bezel.getchannel("A").point(lambda a: 255 if a < 250 else 0)
    w, h = alpha.size
    seed = (w // 2, int(h * 0.6))
    ImageDraw.floodfill(alpha, seed, 128)
    return alpha.point(lambda v: 255 if v == 128 else 0)


def device(kind: str, color: str, screen: Image.Image) -> Image.Image:
    bezel = Image.open(BEZELS / (MAC if kind == "mac" else PHONE)[color]).convert("RGBA")
    mask = screen_mask(bezel)
    l, t, r, b = mask.getbbox()
    layer = Image.new("RGBA", bezel.size, (0, 0, 0, 0))
    shot = screen.convert("RGBA").resize((r - l, b - t), Image.LANCZOS)
    layer.paste(shot, (l, t), mask.crop((l, t, r, b)))
    layer.alpha_composite(bezel)
    return layer


# ---------------------------------------------------------------- 화면 캡처
def login(api: str, who: str) -> dict:
    from backend.app.config import settings

    email, pw = (settings.admin_email, settings.admin_password) if who == "admin" else (settings.demo_email, settings.demo_password)
    r = requests.post(f"{api}/auth/login", json={"email": email, "password": pw}, timeout=60)
    r.raise_for_status()
    return r.json()


def capture(base: str) -> dict:
    from playwright.sync_api import sync_playwright

    api = base.rstrip("/") + "/api/v1"
    items = requests.get(f"{api}/products", params={"region": "국내", "sort": "depart", "size": 50}, timeout=60).json()["items"]
    pid = next((i["id"] for i in items if requests.get(f"{api}/products/{i['id']}", timeout=30).json().get("flights")), None)
    if pid is None:  # 현재 특가에 국내 상품이 없으면 할인율 1위 상품
        pid = requests.get(f"{api}/products", params={"sort": "discount", "size": 1}, timeout=60).json()["items"][0]["id"]
    tokens = {w: login(api, w) for w in ("demo", "admin")}
    shots = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for name, path, who in PAGES:
                for kind, ((w, h), scale) in (("desk", DESK), ("mobile", MOBILE)):
                    mobile = kind == "mobile"
                    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale, is_mobile=mobile,
                                              has_touch=mobile, locale="ko-KR", timezone_id="Asia/Seoul")
                    try:
                        if who:
                            t = tokens[who]
                            ctx.add_init_script(f"localStorage.setItem('np_token', {json.dumps(t['access_token'])});"
                                                f"localStorage.setItem('np_user', {json.dumps(json.dumps(t['user']))});")
                        page = ctx.new_page()
                        page.goto(base.rstrip("/") + path.format(pid=pid), wait_until="networkidle")
                        page.wait_for_timeout(2500)
                        shots[(name, kind)] = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                        if mobile:  # 아래로 스크롤한 화면 (두 번째 폰용)
                            page.mouse.wheel(0, 900)
                            page.wait_for_timeout(1500)
                            shots[(name, "mobile_scroll")] = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    finally:
                        ctx.close()
                print("캡처", name)
        finally:
            browser.close()
    return shots


# ---------------------------------------------------------------- 합성
def compose(name: str, shots: dict) -> Image.Image:
    parts = []
    for kind, color, key, x, y, height in LAYOUTS[name]:
        im = device(kind, color, shots[(name, key)])
        im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
        parts.append((im, x, y))
    W = max(x + im.width for im, x, _ in parts) + 120
    H = max(y + im.height for im, _, y in parts) + 160
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for im, x, y in parts:  # 기기마다 부드러운 그림자 → 기기
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.paste((0, 0, 0, 120), (x + 30, y + 50), im.getchannel("A"))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(40)))
        canvas.alpha_composite(im, (x, y))
    canvas = canvas.crop(canvas.getbbox())
    return canvas.resize((1600, int(canvas.height * 1600 / canvas.width)), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    ensure_bezels()
    shots = capture(args.base)
    for name, *_ in PAGES:
        out = OUT / f"mockup_{name}.png"
        compose(name, shots).save(out, optimize=True)
        print(f"{out.name} {out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()

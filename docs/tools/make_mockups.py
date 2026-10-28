"""반응형 화면 목업 이미지 생성 - 노트북 + 스마트폰 안에 실제 서비스 화면을 넣은 PNG.

    .venv\\Scripts\\python.exe docs\\tools\\make_mockups.py [--base http://127.0.0.1:8000]

결과: docs/md/images/mockup_{index,recommend,product,admin}.png (GitHub Pages 핵심 기능·발표자료에 사용)
"""
import argparse
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "md" / "images"
DESK, MOBILE = (1440, 900), (390, 844)
PAGES = [("index", "/index.html", None), ("recommend", "/recommend.html", "demo"),
         ("product", "/product.html?id={domestic}", "demo"), ("admin", "/admin.html", "admin")]


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
    domestic = next((i["id"] for i in items if requests.get(f"{api}/products/{i['id']}", timeout=30).json().get("flights")), None)
    if domestic is None:  # 현재 특가에 국내 상품이 없으면 할인율 1위 상품
        domestic = requests.get(f"{api}/products", params={"sort": "discount", "size": 1}, timeout=60).json()["items"][0]["id"]
    tokens = {w: login(api, w) for w in ("demo", "admin")}
    shots = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for name, path, who in PAGES:
                for kind, (w, h), scale, mobile in (("desk", DESK, 1, False), ("mobile", MOBILE, 2, True)):
                    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale, is_mobile=mobile,
                                              has_touch=mobile, locale="ko-KR", timezone_id="Asia/Seoul")
                    try:
                        if who:
                            t = tokens[who]
                            ctx.add_init_script(f"localStorage.setItem('np_token', {json.dumps(t['access_token'])});"
                                                f"localStorage.setItem('np_user', {json.dumps(json.dumps(t['user']))});")
                        page = ctx.new_page()
                        page.goto(base.rstrip("/") + path.format(domestic=domestic), wait_until="networkidle")
                        page.wait_for_timeout(2500)
                        shots[(name, kind)] = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
                    finally:
                        ctx.close()
                print("캡처", name)
        finally:
            browser.close()
    return shots


def rounded(im: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def compose(desk: Image.Image, mobile: Image.Image) -> Image.Image:
    W, H = 2000, 1320
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((90, 70, 1790, 1150), 40, fill=(0, 0, 0, 150))
    sd.rounded_rectangle((1555, 470, 1965, 1300), 60, fill=(0, 0, 0, 170))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)))

    # 노트북: 베젤 + 화면 + 카메라 + 받침
    d = ImageDraw.Draw(canvas)
    lx, ly, lw, lh = 120, 30, 1640, 1050
    d.rounded_rectangle((lx, ly, lx + lw, ly + lh), 34, fill=(24, 27, 36, 255), outline=(70, 76, 92, 255), width=3)
    d.ellipse((lx + lw // 2 - 7, ly + 12, lx + lw // 2 + 7, ly + 26), fill=(60, 66, 80, 255))
    screen = desk.resize((lw - 60, lh - 70), Image.LANCZOS)
    canvas.alpha_composite(rounded(screen, 6), (lx + 30, ly + 40))
    d.rounded_rectangle((20, ly + lh - 4, W - 160, ly + lh + 34), 18, fill=(196, 201, 212, 255))
    d.rectangle((20, ly + lh - 4, W - 160, ly + lh + 6), fill=(150, 156, 170, 255))
    cx = (20 + W - 160) // 2
    d.rounded_rectangle((cx - 130, ly + lh - 4, cx + 130, ly + lh + 12), 8, fill=(128, 134, 148, 255))

    # 스마트폰: 베젤 + 화면 + 다이내믹 아일랜드
    px, py, pw_, ph = 1570, 450, 390, 830
    d.rounded_rectangle((px, py, px + pw_, py + ph), 62, fill=(12, 13, 18, 255), outline=(90, 96, 110, 255), width=4)
    phone = mobile.resize((pw_ - 28, ph - 28), Image.LANCZOS)
    canvas.alpha_composite(rounded(phone, 48), (px + 14, py + 14))
    d.rounded_rectangle((px + pw_ // 2 - 58, py + 26, px + pw_ // 2 + 58, py + 58), 16, fill=(0, 0, 0, 255))
    return canvas.resize((1600, int(H * 1600 / W)), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    shots = capture(args.base)
    for name, *_ in PAGES:
        out = OUT / f"mockup_{name}.png"
        compose(shots[(name, "desk")], shots[(name, "mobile")]).save(out, optimize=True)
        print(f"{out.name} {out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()

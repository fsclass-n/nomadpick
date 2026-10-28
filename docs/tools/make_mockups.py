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


def _coeffs(dst, src):
    """dst 사각형 → src 사각형 원근 변환 계수 (Image.transform PERSPECTIVE 용)."""
    import numpy as np

    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(m, float), np.array(src, float).reshape(8)).tolist()


def _warp(im: Image.Image, quad, size) -> Image.Image:
    """이미지를 캔버스(size) 위의 사각형 quad(TL, TR, BR, BL)에 원근 변형하여 붙인다."""
    w, h = im.size
    out = im.convert("RGBA").transform(size, Image.PERSPECTIVE, _coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)]), Image.BICUBIC)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(quad, fill=255)
    out.putalpha(mask)
    return out


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _bilinear(q, u, v):
    """사각형 q(TL, TR, BR, BL) 내부의 (u, v) 위치 → 캔버스 좌표."""
    return _lerp(_lerp(q[0], q[1], u), _lerp(q[3], q[2], u), v)


def _subquad(q, u0, u1, v0, v1):
    return [_bilinear(q, u0, v0), _bilinear(q, u1, v0), _bilinear(q, u1, v1), _bilinear(q, u0, v1)]


def compose(desk: Image.Image, mobile: Image.Image) -> Image.Image:
    """실버 노트북(원근: 화면 + 키보드 + 트랙패드) 앞에 스마트폰이 서 있는 목업."""
    W, H = 1980, 1300
    size = (W, H)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))

    lid = [(330, 40), (1600, 40), (1625, 880), (305, 880)]           # 화면 덮개(위에서 내려다본 원근)
    deck = [(305, 896), (1625, 896), (1840, 1150), (90, 1150)]      # 키보드 몸체(앞쪽이 넓음)
    front = [(90, 1150), (1840, 1150), (1826, 1176), (104, 1176)]   # 몸체 앞면 두께

    # 그림자
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse((60, 1120, 1880, 1250), fill=(0, 0, 0, 120))
    sd.rounded_rectangle((1500, 380, 1930, 1290), 70, fill=(0, 0, 0, 140))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))

    d = ImageDraw.Draw(canvas)
    # 덮개: 알루미늄 테두리 → 검은 베젤 → 화면
    d.polygon(lid, fill=(196, 199, 205, 255))
    bezel = _subquad(lid, 0.006, 0.994, 0.006, 0.996)
    d.polygon(bezel, fill=(14, 15, 18, 255))
    screen_q = _subquad(lid, 0.022, 0.978, 0.042, 0.972)
    canvas.alpha_composite(_warp(desk, screen_q, size))
    cam = _bilinear(lid, 0.5, 0.02)
    d.ellipse((cam[0] - 5, cam[1] - 5, cam[0] + 5, cam[1] + 5), fill=(45, 48, 56, 255))
    # 화면 반사광
    glare = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(glare).polygon([_bilinear(screen_q, 0.55, 0), _bilinear(screen_q, 0.8, 0), _bilinear(screen_q, 0.45, 1), _bilinear(screen_q, 0.2, 1)],
                                  fill=(255, 255, 255, 18))
    canvas.alpha_composite(glare)

    # 힌지
    d.polygon([(305, 880), (1625, 880), (1625, 896), (305, 896)], fill=(70, 72, 78, 255))
    # 몸체 상판(위쪽 어둡고 앞쪽 밝은 그라데이션) + 앞면
    grad = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    steps = 40
    for k in range(steps):
        t0, t1 = k / steps, (k + 1) / steps
        c = int(178 + 40 * t1)
        gd.polygon(_subquad(deck, 0, 1, t0, t1 + 0.002), fill=(c, c + 2, c + 6, 255))
    canvas.alpha_composite(grad)
    d.polygon(front, fill=(150, 153, 160, 255))
    notch = _subquad(front, 0.44, 0.56, 0, 0.55)
    d.polygon(notch, fill=(120, 123, 130, 255))

    # 키보드: 6줄 × 14키 (원근 격자)
    kb = _subquad(deck, 0.115, 0.885, 0.07, 0.56)
    d.polygon(_subquad(kb, -0.01, 1.01, -0.03, 1.03), fill=(150, 153, 160, 255))
    rows, cols, gap = 6, 14, 0.12
    for r in range(rows):
        for c in range(cols):
            u0, u1 = (c + gap / 2) / cols, (c + 1 - gap / 2) / cols
            v0, v1 = (r + gap) / rows, (r + 1 - gap) / rows
            if r == rows - 1 and 4 <= c <= 9:  # 스페이스바
                if c != 4:
                    continue
                u1 = (10 - gap / 2) / cols
            d.polygon(_subquad(kb, u0, u1, v0, v1), fill=(32, 33, 37, 255))
    # 트랙패드
    tp = _subquad(deck, 0.33, 0.67, 0.64, 0.95)
    d.polygon(tp, fill=(206, 209, 215, 255), outline=(160, 163, 170, 255))

    # 스마트폰(정면): 티타늄 테두리 → 검은 베젤 → 화면 → 다이내믹 아일랜드
    px, py, pw_, ph = 1500, 360, 410, 880
    d.rounded_rectangle((px - 4, py - 4, px + pw_ + 4, py + ph + 4), 70, fill=(110, 114, 122, 255))
    d.rounded_rectangle((px, py, px + pw_, py + ph), 66, fill=(8, 8, 10, 255))
    phone = mobile.resize((pw_ - 30, ph - 30), Image.LANCZOS)
    canvas.alpha_composite(rounded(phone, 52), (px + 15, py + 15))
    d.rounded_rectangle((px + pw_ // 2 - 60, py + 30, px + pw_ // 2 + 60, py + 64), 17, fill=(0, 0, 0, 255))

    canvas = canvas.crop(canvas.getbbox())
    return canvas.resize((1600, int(canvas.height * 1600 / canvas.width)), Image.LANCZOS)


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

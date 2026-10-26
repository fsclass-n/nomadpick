"""Mermaid 다이어그램 → PNG (로컬 Chrome/Edge headless + mermaid CDN, 여백 자동 자르기)."""
import html
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{{margin:0;padding:16px;background:#fff;font-family:'Malgun Gothic',sans-serif}}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script></head>
<body><pre class="mermaid">{code}</pre>
<script>mermaid.initialize({{startOnLoad:true,theme:'default',fontFamily:'Malgun Gothic, sans-serif',
flowchart:{{useMaxWidth:false,htmlLabels:true,curve:'basis'}},sequence:{{useMaxWidth:false}},er:{{useMaxWidth:false}},
gantt:{{useMaxWidth:false,barHeight:34,fontSize:16,sectionFontSize:16,leftPadding:120}}}});</script></body></html>"""


def _browser() -> str:
    for b in BROWSERS:
        if Path(b).is_file():
            return b
    raise FileNotFoundError("Chrome/Edge 를 찾을 수 없습니다.")


def render(code: str, width: int = 1600, height: int = 1400, scale: float = 1.0) -> bytes:
    tmpdir = Path(tempfile.mkdtemp(prefix="mmd_"))
    page = tmpdir / "d.html"
    shot = tmpdir / "d.png"
    page.write_text(TEMPLATE.format(code=html.escape(code)), encoding="utf-8")
    subprocess.run([_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmpdir / 'prof'}",
                    f"--force-device-scale-factor={scale}", f"--window-size={width},{height}", "--virtual-time-budget=15000",
                    f"--screenshot={shot}", page.as_uri()], check=True, capture_output=True, timeout=120)
    img = Image.open(shot).convert("RGB")
    diff = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255)))
    box = diff.getbbox()
    if box:
        pad = 12
        img = img.crop((max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, img.width), min(box[3] + pad, img.height)))
    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()

"""HWPX(한글 OWPML) 편집 도구 - 서식(문단·글자 모양, 표 구조)은 그대로 두고 내용만 교체한다.

- subs  : [(old, new)]           각 <hp:t> 텍스트의 부분 문자열 치환 (전역)
- paras : {old_text: new}        문단 전체 텍스트가 old 와 같으면 교체
                                  new 가 str 이면 첫 run 에 넣고 나머지 run 은 비움,
                                  list 이면 run 개수만큼 순서대로 대입(인라인 서식 유지)
- cells : {first_line_prefix: [lines]}  표 셀 첫 문단이 prefix 로 시작하면 셀 문단 전체를 새 줄 목록으로 교체(코드 블록 등)
- images: {binaryItemIDRef: png_bytes}  그림 교체(표시 폭 유지, 비율에 맞게 높이 조정)
"""
import copy
import struct
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}
HP = "{%s}" % NS["hp"]
HC = "{%s}" % NS["hc"]


def _runs_t(p):
    return [t for run in p.findall("hp:run", NS) for t in run.findall("hp:t", NS)]


def _t_text(t) -> str:
    return "".join(t.itertext())


def _set_t(t, text: str) -> None:
    for child in list(t):
        t.remove(child)
    t.text = text


def para_text(p) -> str:
    return "".join(_t_text(t) for t in _runs_t(p)).replace("\xa0", " ")


def png_size(data: bytes) -> tuple[int, int]:
    w, h = struct.unpack(">II", data[16:24])
    return w, h


class HwpxDoc:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as z:
            self.infos = z.infolist()
            self.data = {i.filename: z.read(i.filename) for i in self.infos}
        self.root = etree.fromstring(self.data["Contents/section0.xml"])
        self.used: set[str] = set()

    # ---------- text ----------
    def apply_subs(self, subs: list[tuple[str, str]]) -> None:
        for t in self.root.iter(HP + "t"):
            text = _t_text(t)
            new = text
            for old, rep in subs:
                new = new.replace(old, rep)
            if new != text:
                _set_t(t, new)

    def apply_paras(self, paras: dict) -> None:
        for p in self.root.iter(HP + "p"):
            key = para_text(p)
            if key not in paras:
                continue
            new = paras[key]
            ts = _runs_t(p)
            if isinstance(new, list):
                if len(new) != len(ts):
                    raise ValueError(f"run 개수 불일치({len(ts)}): {key}")
                for t, s in zip(ts, new):
                    _set_t(t, s)
            else:
                _set_t(ts[0], new)
                for t in ts[1:]:
                    _set_t(t, "")
            self.used.add(key)

    def apply_cells(self, cells: dict) -> None:
        for tc in self.root.iter(HP + "tc"):
            sub = tc.find("hp:subList", NS)
            if sub is None:
                continue
            ps = sub.findall("hp:p", NS)
            if not ps:
                continue
            first = para_text(ps[0]).strip()
            key = next((k for k in cells if first.startswith(k)), None)
            if key is None:
                continue
            lines = cells[key]
            template = ps[0]
            for p in ps:
                sub.remove(p)
            for i, line in enumerate(lines):
                p = copy.deepcopy(template)
                p.set("id", str(2147480000 + i))
                ts = _runs_t(p)
                _set_t(ts[0], line)
                for t in ts[1:]:
                    _set_t(t, "")
                for nested in p.iter(HP + "tbl"):
                    nested.getparent().remove(nested)
                sub.append(p)
            self.used.add(key)

    def unused(self, *specs: dict) -> list[str]:
        return [k for spec in specs for k in spec if k not in self.used]

    # ---------- image ----------
    def replace_image(self, item_id: str, png: bytes, max_height_ratio: float = 1.6) -> None:
        name = f"BinData/{item_id}.png"
        if name not in self.data:
            raise KeyError(name)
        self.data[name] = png
        w_px, h_px = png_size(png)
        for pic in self.root.iter(HP + "pic"):
            img = pic.find("hc:img", NS)
            if img is None or img.get("binaryItemIDRef") != item_id:
                continue
            sz = pic.find("hp:sz", NS)
            width, height = int(sz.get("width")), int(sz.get("height"))
            new_w, new_h = width, int(width * h_px / w_px)
            if new_h > height * max_height_ratio:
                new_h = int(height * max_height_ratio)
                new_w = int(new_h * w_px / h_px)
            for tag in ("hp:sz", "hp:orgSz"):
                el = pic.find(tag, NS)
                el.set("width", str(new_w))
                el.set("height", str(new_h))
            rect = pic.find("hp:imgRect", NS)
            pts = {"pt0": (0, 0), "pt1": (new_w, 0), "pt2": (new_w, new_h), "pt3": (0, new_h)}
            for k, (x, y) in pts.items():
                el = rect.find(f"hc:{k}", NS)
                el.set("x", str(x))
                el.set("y", str(y))
            rot = pic.find("hp:rotationInfo", NS)
            rot.set("centerX", str(new_w // 2))
            rot.set("centerY", str(new_h // 2))

    # ---------- output ----------
    def all_text(self) -> str:
        return "\n".join(t for t in (para_text(p) for p in self.root.iter(HP + "p")) if t.strip())

    def save(self, out: Path) -> None:
        self.data["Contents/section0.xml"] = etree.tostring(self.root, xml_declaration=True, encoding="UTF-8", standalone=True)
        if "Preview/PrvText.txt" in self.data:
            self.data["Preview/PrvText.txt"] = self.all_text()[:1500].encode("utf-16-le") \
                if self.data["Preview/PrvText.txt"][:2] in (b"\xff\xfe",) else self.all_text()[:1500].encode("utf-8")
        tmp = Path(str(out) + ".tmp")
        with zipfile.ZipFile(tmp, "w") as z:
            for info in self.infos:
                comp = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
                z.writestr(zipfile.ZipInfo(info.filename, date_time=info.date_time), self.data[info.filename], compress_type=comp)
        tmp.replace(out)

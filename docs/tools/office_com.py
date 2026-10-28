"""한컴오피스(HWPFrame.HwpObject)·PowerPoint COM 자동화 - hwpx/pptx → PDF 변환 (Windows 전용).

한글 자동화의 '파일 접근 허용' 보안 대화상자는 보안 모듈이 없으면 매번 표시되므로,
백그라운드 스레드가 대화상자의 [모두 허용]/[허용] 버튼을 자동으로 누른다.
"""
import threading
import time
from pathlib import Path

import pythoncom
import win32con
import win32gui
import win32com.client

ALLOW_LABELS = ("모두 허용", "허용", "접근 허용", "예(&Y)", "확인")


class DialogClicker(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.clicked = 0

    def _scan_children(self, hwnd):
        found = []

        def cb(child, _):
            if win32gui.GetClassName(child) == "Button":
                text = win32gui.GetWindowText(child).replace("&", "")
                found.append((child, text))
            return True

        try:
            win32gui.EnumChildWindows(hwnd, cb, None)
        except Exception:
            pass
        return found

    def _scan(self):
        def cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if win32gui.GetClassName(hwnd) != "#32770" and "한글" not in title:
                return True
            buttons = self._scan_children(hwnd)
            texts = [t for _, t in buttons]
            if not any("허용" in t for t in texts):
                return True
            for label in ALLOW_LABELS:
                for child, text in buttons:
                    if text.replace("(A)", "").replace("(Y)", "").strip() == label.replace("(&Y)", ""):
                        win32gui.SendMessage(child, win32con.BM_CLICK, 0, 0)
                        self.clicked += 1
                        return True
            return True

        win32gui.EnumWindows(cb, None)

    def run(self):
        while not self._stop.is_set():
            try:
                self._scan()
            except Exception:
                pass
            time.sleep(0.3)

    def stop(self):
        self._stop.set()


class Hwp:
    def __init__(self, visible: bool = False) -> None:
        pythoncom.CoInitialize()
        self.clicker = DialogClicker()
        self.clicker.start()
        self.hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        try:
            self.hwp.XHwpWindows.Item(0).Visible = visible
        except Exception:
            pass
        try:
            self.hwp.SetMessageBoxMode(0x00020000 | 0x00000010)  # 메시지 박스 자동 '예/확인'
        except Exception:
            pass

    def open(self, path: Path) -> None:
        if not self.hwp.Open(str(path), "HWPX", "forceopen:true"):
            raise RuntimeError(f"열기 실패: {path}")

    def save_as(self, path: Path, fmt: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.hwp.SaveAs(str(path), fmt, ""):
            raise RuntimeError(f"저장 실패: {path} ({fmt})")

    def close(self) -> None:
        try:
            self.hwp.Clear(1)
            self.hwp.Quit()
        finally:
            self.clicker.stop()


def hwpx_refresh_and_pdf(items: list[tuple[Path, Path]]) -> None:
    """(hwpx, pdf) 목록 - 한글에서 열어 hwpx 재저장(레이아웃·미리보기 갱신) 후 PDF 저장."""
    app = Hwp()
    try:
        for src, pdf in items:
            app.open(src)
            app.save_as(src, "HWPX")
            app.save_as(pdf, "PDF")
            app.hwp.Clear(1)
            print("PDF:", pdf)
    finally:
        app.close()


def pptx_animate(src: Path) -> None:
    """발표용 애니메이션: 슬라이드 전환(부드럽게 페이드) + 제목·부제 페이드 → 본문 요소가 아래에서 차례로 등장.

    모든 효과는 '이전 효과 다음'으로 자동 진행 → 클릭/→ 키는 다음 슬라이드로 넘어갈 때만 사용.
    상단 바·구분선·푸터·쪽번호는 고정.
    """
    pythoncom.CoInitialize()
    ppt = win32com.client.gencache.EnsureDispatch("PowerPoint.Application")
    C = win32com.client.constants
    fixed = {"Rectangle 1", "Rectangle 2", "Connector 5", "TextBox 6", "TextBox 7"}
    pres = ppt.Presentations.Open(str(src), WithWindow=False)
    try:
        for slide in pres.Slides:
            t = slide.SlideShowTransition
            t.EntryEffect = C.ppEffectFadeSmoothly
            t.Duration = 0.7
            seq = slide.TimeLine.MainSequence
            for k in range(seq.Count, 0, -1):
                seq.Item(k).Delete()
            shapes = [s for s in slide.Shapes if s.Name not in fixed]
            first = slide.SlideIndex == 1 or slide.SlideIndex == pres.Slides.Count
            for i, shp in enumerate(shapes):
                is_title = shp.Name in {"TextBox 3", "TextBox 4"}
                if first or is_title:
                    eff = seq.AddEffect(shp, C.msoAnimEffectFade, 0, C.msoAnimTriggerAfterPrevious)
                    eff.Timing.Duration = 0.6
                elif shp.HasTable or shp.Type == 13:  # 표·그림: 확대 등장
                    eff = seq.AddEffect(shp, C.msoAnimEffectZoom, 0, C.msoAnimTriggerAfterPrevious)
                    eff.Timing.Duration = 0.6
                else:  # 카드·수치·설명: 아래에서 떠오르기
                    eff = seq.AddEffect(shp, C.msoAnimEffectFly, 0, C.msoAnimTriggerAfterPrevious)
                    eff.EffectParameters.Direction = C.msoAnimDirectionBottom
                    eff.Timing.Duration = 0.35 if len(shapes) <= 12 else 0.18  # 요소가 많은 슬라이드는 빠르게
                eff.Timing.TriggerDelayTime = (0.05 if len(shapes) <= 12 else 0) if i else 0.2
        pres.Save()
        print("애니메이션:", src.name, pres.Slides.Count, "슬라이드")
    finally:
        pres.Close()
        if ppt.Presentations.Count == 0:
            ppt.Quit()


def pptx_to_pdf(src: Path, pdf: Path) -> None:
    pythoncom.CoInitialize()
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    pres = ppt.Presentations.Open(str(src), WithWindow=False)
    try:
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pres.SaveAs(str(pdf), 32)  # ppSaveAsPDF
        print("PDF:", pdf)
    finally:
        pres.Close()
        if ppt.Presentations.Count == 0:
            ppt.Quit()

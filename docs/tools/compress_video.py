"""시연 영상을 GitHub 업로드 용량(기본 90MB 이하)에 맞게 압축 - FFmpeg H.264 2-pass + AAC.

    python docs/tools/compress_video.py 원본.mp4 docs/video/nomadpick_demo.mp4 --target-mb 90 [--height 1080]

FFmpeg 설치: winget install Gyan.FFmpeg (Windows) / sudo apt install ffmpeg (Ubuntu)
"""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def duration_sec(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="GitHub 업로드용 MP4 압축")
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--target-mb", type=float, default=90.0, help="목표 용량(MB), GitHub 단일 파일 한도는 100MB")
    ap.add_argument("--height", type=int, default=1080, help="최대 세로 해상도 (1080 또는 720)")
    ap.add_argument("--audio-kbps", type=int, default=128)
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg/ffprobe 를 찾을 수 없습니다. 먼저 FFmpeg 를 설치하세요 (winget install Gyan.FFmpeg).")

    sec = duration_sec(args.src)
    total_kbps = args.target_mb * 8 * 1024 / sec          # 목표 용량 → 전체 비트레이트
    video_kbps = int(total_kbps * 0.97 - args.audio_kbps)  # 컨테이너 여유 3%
    if video_kbps < 300:
        raise SystemExit(f"목표 용량이 너무 작습니다 (영상 {video_kbps}kbps). --target-mb 를 늘리거나 --height 720 을 사용하세요.")
    print(f"길이 {sec / 60:.1f}분 → 영상 {video_kbps}kbps + 음성 {args.audio_kbps}kbps (목표 {args.target_mb}MB)")

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=-2:'min({args.height},ih)',fps=30"
    common = ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{video_kbps}k", "-vf", vf, "-pix_fmt", "yuv420p"]
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "ffmpeg2pass")
        subprocess.run(["ffmpeg", "-y", "-i", str(args.src), *common, "-pass", "1", "-passlogfile", log, "-an",
                        "-f", "mp4", os.devnull], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(args.src), *common, "-pass", "2", "-passlogfile", log,
                        "-c:a", "aac", "-b:a", f"{args.audio_kbps}k", "-movflags", "+faststart", str(args.dst)], check=True)

    size_mb = args.dst.stat().st_size / 1024 / 1024
    status = "OK" if size_mb < 100 else "초과 - --target-mb 를 줄여 다시 실행하세요"
    print(f"{args.dst} : {size_mb:.1f}MB ({status})")


if __name__ == "__main__":
    main()

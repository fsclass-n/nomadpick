# NomadPick - FastAPI(API + 정적 프런트엔드) + RPA 스케줄러(Playwright) 단일 컨테이너
# Render(Docker 런타임, 무료 RAM 512MB) / AWS EC2(docker compose) 공용
# Microsoft 공식 Playwright 이미지: Chromium·시스템 의존성 사전 설치 (requirements.txt 의 playwright==1.49.1 과 버전 일치)
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Seoul \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    # glibc 메모리 단편화 억제 (512MB 환경)
    MALLOC_ARENA_MAX=2 \
    # 저메모리 수집 기본값: 렌더링에 필요 없는 리소스 차단
    PLAYWRIGHT_BLOCK_MEDIA=true \
    PLAYWRIGHT_BLOCK_TYPES=image,media,font,stylesheet,texttrack,manifest \
    PLAYWRIGHT_TIMEOUT_MS=30000 \
    # RPA 는 별도 저우선순위 프로세스로 실행: 15분·300MB 를 넘으면 Chromium 까지 강제 종료 → 웹 서버 502 방지
    RPA_ISOLATED=true \
    RPA_JOB_TIMEOUT_SEC=900 \
    RPA_AGENCY_TIMEOUT_SEC=240 \
    RPA_MEMORY_LIMIT_MB=300 \
    RPA_RETRIES=1

# 리포트 차트(Matplotlib/Seaborn)·브라우저 한글 폰트, 시간대
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-nanum tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Ubuntu 24.04(PEP 668) 시스템 Python 에 설치. 브라우저는 이미지에 포함되어 있어 다시 받지 않는다.
RUN python3 -m pip install --break-system-packages -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY rpa ./rpa

# 이미지 기본 사용자(pwuser)로 실행 - root 가 아니어도 --no-sandbox 옵션으로 Chromium 동작
RUN chown -R pwuser:pwuser /app
USER pwuser

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=40s \
    CMD python3 -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/v1/health' % os.getenv('PORT', '8000'), timeout=4)"

# 스케줄러 중복 실행 방지 + 메모리 절약을 위해 워커 1개로 실행
CMD ["sh", "-c", "python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]

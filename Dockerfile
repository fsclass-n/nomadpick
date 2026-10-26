# NomadPick - FastAPI(API + 정적 프런트엔드) + RPA 스케줄러(Playwright) 단일 컨테이너
# Render(Docker 런타임) / AWS EC2(docker compose) 공용
FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 리포트 차트(Matplotlib/Seaborn)·브라우저 한글 폰트, 시간대
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-nanum tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY backend ./backend
COPY frontend ./frontend
COPY rpa ./rpa

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=40s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/v1/health' % os.getenv('PORT', '8000'), timeout=4)"

# 스케줄러 중복 실행 방지를 위해 워커 1개로 실행
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

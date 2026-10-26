"""NomadPick FastAPI 애플리케이션 - REST API(/api/v1) + 정적 프런트엔드(/)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import FRONTEND_DIR, settings
from .database import SessionLocal, engine, init_db
from .routers import admin, auth, favorites, preferences, products, recommendations, rpa
from .scheduler import start_scheduler, stop_scheduler
from .services.bootstrap import seed_reference_data
from .utils import now_kst

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_reference_data(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="NomadPick API",
    description="RPA 기반 개인 맞춤형 여행상품 추천 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://([a-z0-9-]+--)?(nomadpick|noamdpick)\.netlify\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return JSONResponse(detail, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:])
    return JSONResponse({"code": "VALIDATION_ERROR", "message": f"{field}: {first.get('msg', '입력값 오류')}"}, status_code=422)


@app.get(f"{API_PREFIX}/health", tags=["상태"], summary="헬스 체크")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": "tidb",
            "db_ok": db_ok, "env": settings.app_env, "time": now_kst().isoformat()}


for r in (auth.router, preferences.router, products.router, recommendations.router, favorites.router, rpa.router, admin.router):
    app.include_router(r, prefix=API_PREFIX)

# 정적 프런트엔드 (Render / EC2 단일 도메인 서비스). Netlify 는 frontend/ 폴더만 별도 배포.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

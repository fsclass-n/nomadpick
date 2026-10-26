"""환경 변수 로딩.

- 로컬 · EC2 : 프로젝트 루트의 .env 파일
- Render     : 대시보드 Environment 에 .env 내용을 붙여넣어 등록한 환경 변수 (.env 파일 없음)
이미 설정된 OS 환경 변수가 .env 보다 우선한다.
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"

if (ROOT_DIR / ".env").is_file():
    load_dotenv(ROOT_DIR / ".env", override=False)

# Windows CRT 는 IANA 형식 TZ(Asia/Seoul)를 해석하지 못해 로컬 시각이 UTC 로 바뀌므로 제거한다.
# (서비스 시간대는 settings.timezone / utils.KST 로 처리, Linux 컨테이너에서는 TZ 를 그대로 사용)
_TZ = os.getenv("TZ", "Asia/Seoul")
if os.name == "nt":
    os.environ.pop("TZ", None)

DEFAULT_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "local")
        self.app_name = os.getenv("APP_NAME", "NomadPick")
        self.timezone = _TZ
        # TiDB Cloud (MySQL 8.x 호환) - 로컬 테스트 포함 모든 환경에서 TiDB 사용
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.db_ssl = _bool("DB_SSL", True)
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-secret")
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
        self.rpa_api_key = os.getenv("RPA_API_KEY", "dev-rpa-key")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@nomadpick.example.com")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.demo_email = os.getenv("DEMO_EMAIL", "demo@nomadpick.example.com")
        self.demo_password = os.getenv("DEMO_PASSWORD", "")
        self.cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
        self.data_go_kr_key = os.getenv("DATA_GO_KR_KEY", "").strip()
        self.rpa_source_mode = os.getenv("RPA_SOURCE_MODE", "auto")
        self.rpa_sink = os.getenv("RPA_SINK", "direct")
        self.api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.request_interval_sec = float(os.getenv("REQUEST_INTERVAL_SEC", "2"))
        self.rpa_user_agent = os.getenv("RPA_USER_AGENT", "").strip() or DEFAULT_BROWSER_UA
        self.playwright_headless = _bool("PLAYWRIGHT_HEADLESS", True)
        self.playwright_channel = os.getenv("PLAYWRIGHT_CHANNEL", "chromium").strip() or None
        self.playwright_timeout_ms = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "45000"))
        self.playwright_block_media = _bool("PLAYWRIGHT_BLOCK_MEDIA", True)
        self.enable_scheduler = _bool("ENABLE_SCHEDULER", False)
        self.collect_on_startup = _bool("COLLECT_ON_STARTUP", False)

    def require_database_url(self) -> str:
        if not self.database_url.startswith("mysql"):
            raise RuntimeError(
                "DATABASE_URL 이 설정되지 않았습니다. TiDB 접속 정보를 입력하세요. "
                "예) mysql+pymysql://<user>:<password>@gateway01.<region>.prod.aws.tidbcloud.com:4000/nomadpick")
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

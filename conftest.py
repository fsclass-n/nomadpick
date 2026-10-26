"""pytest 공통 설정 - TiDB 테스트 전용 데이터베이스 사용 (SQLite 미사용).

- TEST_DATABASE_URL 이 있으면 사용, 없으면 DATABASE_URL 과 같은 TiDB 클러스터의 'nomadpick_test' DB 를 자동 생성
- 운영 DB(nomadpick)는 건드리지 않으며, 테스트 시작 시 테스트 DB 의 테이블을 모두 지우고 다시 만든다
- DB 접속 정보가 없으면 DB 가 필요한 backend/tests 는 건너뛰고 RPA 파서 테스트만 실행한다
"""
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
_env = {**dotenv_values(ROOT / ".env"), **os.environ}


def _test_db_url() -> str | None:
    url = (_env.get("TEST_DATABASE_URL") or "").strip()
    if url:
        return url
    base = (_env.get("DATABASE_URL") or "").strip()
    if not base.startswith("mysql"):
        return None
    return make_url(base).set(database="nomadpick_test").render_as_string(hide_password=False)


TEST_DB_URL = _test_db_url()
collect_ignore = [] if TEST_DB_URL else ["backend/tests"]

os.environ.update({
    "DATABASE_URL": TEST_DB_URL or "",
    "ENABLE_SCHEDULER": "false",
    "COLLECT_ON_STARTUP": "false",
    "RPA_SOURCE_MODE": "sample",
    "RPA_SINK": "direct",
    "RPA_API_KEY": "test-rpa-key",
    "JWT_SECRET": "test-secret",
    "ADMIN_EMAIL": "admin@test.com",
    "ADMIN_PASSWORD": "Admin!2026",
    "DEMO_EMAIL": "demo@test.com",
    "DEMO_PASSWORD": "Demo!2026",
    "DATA_GO_KR_KEY": "",
    "REQUEST_INTERVAL_SEC": "0",
})


def pytest_configure(config):
    if not TEST_DB_URL:
        print("\n[conftest] DATABASE_URL(TiDB) 미설정 → backend/tests 건너뜀")
        return
    import certifi
    from sqlalchemy import create_engine, text

    url = make_url(TEST_DB_URL)
    if not (url.database or "").endswith("_test"):  # 운영 DB 보호
        raise RuntimeError(f"테스트 DB 이름은 '_test' 로 끝나야 합니다: {url.database}")
    ssl = {"ssl": {"ca": certifi.where()}} if (_env.get("DB_SSL", "true").lower() != "false") else {}
    server = create_engine(url.set(database=""), connect_args={"charset": "utf8mb4", **ssl})
    with server.begin() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{url.database}`"))
        conn.execute(text(f"CREATE DATABASE `{url.database}` DEFAULT CHARACTER SET utf8mb4"))
    server.dispose()

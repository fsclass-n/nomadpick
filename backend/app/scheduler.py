"""서버 내장 RPA 스케줄러 (APScheduler).

BOT-01 특가 수집   : 30분 주기 (09~21시)
BOT-02 공공데이터  : 매일 07:00 (국토교통부 국내항공운항정보)
BOT-03 일일 리포트 : 매일 21:30
"""
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from .config import settings
from .database import SessionLocal
from .models import TravelProduct

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run(job: str) -> None:
    from rpa.run import run_job_isolated

    try:
        run_job_isolated(job)  # 별도 프로세스 + 시간·메모리 한도 → 웹 서버(헬스 체크) 보호
    except Exception:  # 스케줄러 스레드가 죽지 않도록 방어
        log.exception("RPA job 실패: %s", job)


def start_scheduler() -> None:
    global _scheduler
    if settings.enable_scheduler and _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=settings.timezone)
        _scheduler.add_job(_run, CronTrigger(minute="0,30", hour="9-21"), args=["deals"], id="BOT-01", max_instances=1, coalesce=True)
        _scheduler.add_job(_run, CronTrigger(hour=7, minute=0), args=["public"], id="BOT-02", max_instances=1, coalesce=True)
        _scheduler.add_job(_run, CronTrigger(hour=21, minute=30), args=["report"], id="BOT-03", max_instances=1, coalesce=True)
        _scheduler.start()
        log.info("RPA 스케줄러 시작 (%s)", settings.timezone)

    if settings.collect_on_startup:
        with SessionLocal() as db:
            empty = (db.scalar(select(func.count()).select_from(TravelProduct).where(TravelProduct.is_active.is_(True))) or 0) == 0
        if empty:
            log.info("활성 상품이 없어 최초 수집을 실행합니다.")
            threading.Thread(target=_run, args=("all",), daemon=True).start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

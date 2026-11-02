"""서버 내장 RPA 스케줄러 (APScheduler).

BOT-01 특가 수집   : 30분 주기 (09~21시)
BOT-02 공공데이터  : 매일 07:00 (국토교통부 국내항공운항정보)
BOT-03 일일 리포트 : 매일 21:30

서버 2대 혼용(같은 TiDB): RPA_ROLE=primary(EC2·Playwright, 정각/30분 항상 수집)
                         RPA_ROLE=fallback(Render·HTTP, 15/45분에 확인 → primary 수집 공백이 있는 여행사만 대신 수집,
                                           BOT-02 08:00 · BOT-03 21:50 에 오늘 실행 기록이 없을 때만)
"""
import logging
import threading
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from .config import settings
from .database import SessionLocal
from .models import TravelProduct

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def fallback_targets(job: str, db=None) -> list[str] | None:
    """fallback 서버가 대신 실행할 대상. None = 실행 불필요(다른 서버가 최근에 성공).

    deals  : 최근 RPA_FALLBACK_STALE_MIN(25)분 안에 live 수집에 성공한 기록이 없는 여행사만
             (15분 전 primary 실행은 포함, 30분 전 자기 실행은 제외 → primary 가 없으면 30분마다 직접 수집)
    public : 오늘 BOT-02 성공 기록이 없을 때 / report : 오늘 리포트가 없을 때
    """
    from .constants import AGENCIES
    from .models import ExcelReport, RpaJobLog
    from .utils import now_kst, today_kst

    own = db is None
    db = db or SessionLocal()
    try:
        if job == "deals":
            since = now_kst() - timedelta(minutes=settings.rpa_fallback_stale_min)
            fresh = set(db.scalars(select(RpaJobLog.agency_id).where(
                RpaJobLog.job_name == "BOT-01", RpaJobLog.status.in_(("SUCCESS", "WARN")), RpaJobLog.source == "live",
                RpaJobLog.collected > 0, RpaJobLog.started_at >= since)).all())
            stale = [a["code"] for a in AGENCIES if a["id"] not in fresh]
            return stale or None
        if job == "public":
            done = db.scalar(select(func.count()).select_from(RpaJobLog).where(
                RpaJobLog.job_name == "BOT-02", RpaJobLog.status.in_(("SUCCESS", "WARN")),
                RpaJobLog.started_at >= datetime.combine(today_kst(), datetime.min.time())))
            return None if done else []
        if job == "report":
            return None if db.scalar(select(ExcelReport.id).where(ExcelReport.report_date == today_kst())) else []
        return []
    finally:
        if own:
            db.close()


def _run(job: str) -> None:
    from rpa.run import run_job_isolated

    try:
        agencies = None
        if settings.rpa_role == "fallback":
            targets = fallback_targets(job)
            if targets is None:
                log.info("[fallback] %s 건너뜀 - 다른 서버(primary)가 최근에 수집함", job)
                return
            agencies = targets or None
            log.info("[fallback] primary 수집 공백 → 대신 실행: %s %s", job, targets or "")
        run_job_isolated(job, agencies)  # 별도 프로세스 + 시간·메모리 한도 → 웹 서버(헬스 체크) 보호
    except Exception:  # 스케줄러 스레드가 죽지 않도록 방어
        log.exception("RPA job 실패: %s", job)


def start_scheduler() -> None:
    global _scheduler
    if settings.enable_scheduler and _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=settings.timezone)
        fallback = settings.rpa_role == "fallback"
        if settings.enable_deals_job:
            _scheduler.add_job(_run, CronTrigger(minute=settings.rpa_deals_minutes, hour="9-21"), args=["deals"], id="BOT-01",
                               max_instances=1, coalesce=True)
        else:
            log.info("BOT-01 특가 수집은 이 서버에서 실행하지 않습니다 (ENABLE_DEALS_JOB=false)")
        # fallback 은 primary 보다 늦게 확인해서 primary 가 이미 실행했으면 건너뜀
        _scheduler.add_job(_run, CronTrigger(hour=8 if fallback else 7, minute=0), args=["public"], id="BOT-02", max_instances=1, coalesce=True)
        _scheduler.add_job(_run, CronTrigger(hour=21, minute=50 if fallback else 30), args=["report"], id="BOT-03", max_instances=1, coalesce=True)
        _scheduler.start()
        log.info("RPA 스케줄러 시작 (%s) - 역할 %s · 엔진 %s · 특가 수집 매시 %s분", settings.timezone, settings.rpa_role,
                 settings.rpa_engine, settings.rpa_deals_minutes)

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

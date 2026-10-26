"""관리자 - 수집 모니터링, 일일 리포트, 수동 실행."""
from collections import defaultdict
from datetime import date, timedelta
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..constants import AGENCIES
from ..database import get_db
from ..models import ExcelReport, RpaJobLog
from ..security import api_error, get_admin
from ..utils import today_kst

router = APIRouter(prefix="/admin", tags=["관리자"], dependencies=[Depends(get_admin)])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _rate(ok: int, total: int) -> float:
    return round(ok / total * 100, 1) if total else 0.0


@router.get("/rpa-logs", summary="수집 이력·통계")
def rpa_logs(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    since = today_kst() - timedelta(days=days - 1)
    logs = db.scalars(select(RpaJobLog).options(joinedload(RpaJobLog.agency))
                      .where(RpaJobLog.started_at >= since).order_by(RpaJobLog.started_at.desc())).all()
    today = today_kst()
    deal_logs = [l for l in logs if l.job_name == "BOT-01"]
    today_deals = [l for l in deal_logs if l.started_at.date() == today]

    agencies = []
    for a in AGENCIES:
        mine = [l for l in deal_logs if l.agency_id == a["id"]]
        last = mine[0] if mine else None
        agencies.append({
            "name": a["name"], "code": a["code"],
            "last_run": last.started_at.isoformat() if last else None,
            "status": last.status if last else "NONE", "source": last.source if last else None,
            "runs": len(mine), "success_rate": _rate(sum(l.status == "SUCCESS" for l in mine), len(mine)),
            "collected": sum(l.collected for l in mine), "failed": sum(l.failed for l in mine),
        })

    daily = defaultdict(lambda: {"collected": 0, "failed": 0, "runs": 0})
    for l in deal_logs:
        d = daily[l.started_at.date().isoformat()]
        d["collected"] += l.collected
        d["failed"] += l.failed
        d["runs"] += 1

    collected_today = sum(l.collected for l in today_deals)
    failed_today = sum(l.failed for l in today_deals)
    return {
        "summary": {
            "today_runs": len(today_deals),
            "today_collected": collected_today,
            "success_rate": _rate(sum(l.status == "SUCCESS" for l in deal_logs), len(deal_logs)),
            "parse_fail_rate": _rate(failed_today, collected_today + failed_today),
        },
        "agencies": agencies,
        "daily": [{"date": k, **v} for k, v in sorted(daily.items())],
        "logs": [{
            "id": l.id, "job_name": l.job_name, "agency": l.agency.name if l.agency else "-", "status": l.status,
            "source": l.source, "collected": l.collected, "failed": l.failed, "retries": l.retries, "message": l.message,
            "started_at": l.started_at.isoformat(), "ended_at": l.ended_at.isoformat() if l.ended_at else None,
        } for l in logs[:100]],
    }


@router.get("/reports", summary="일일 리포트 목록")
def list_reports(db: Session = Depends(get_db)):
    rows = db.execute(select(ExcelReport.report_date, ExcelReport.file_name, ExcelReport.summary, ExcelReport.created_at)
                      .order_by(ExcelReport.report_date.desc()).limit(30)).all()
    return [{"report_date": r.report_date.isoformat(), "file_name": r.file_name, "summary": r.summary,
             "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.get("/reports/{report_date}", summary="일일 리포트 다운로드(xlsx / html 차트)")
def get_report(report_date: date, format: str = Query("xlsx", pattern="^(xlsx|html)$"), db: Session = Depends(get_db)):
    row = db.scalar(select(ExcelReport).where(ExcelReport.report_date == report_date))
    if row is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "REPORT_NOT_FOUND", "해당 일자의 리포트가 없습니다.")
    if format == "html":
        return HTMLResponse(row.chart_html or "<p>차트가 없습니다.</p>")
    return Response(row.file_blob, media_type=XLSX,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.file_name)}"})


@router.post("/rpa/run", status_code=status.HTTP_202_ACCEPTED, summary="RPA 수동 실행")
def run_rpa(background: BackgroundTasks, job: str = Query("deals", pattern="^(deals|public|report|all)$")):
    from rpa.run import run_job  # 지연 import (RPA 의존성)

    background.add_task(run_job, job)
    return {"job": job, "status": "ACCEPTED"}

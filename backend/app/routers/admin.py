"""관리자 - 수집 모니터링, 일일 리포트, 수동 실행, 회원 권한 관리."""
import logging
from collections import defaultdict
from datetime import date, timedelta
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..constants import AGENCIES
from ..database import get_db
from ..models import ExcelReport, RpaJobLog, User
from ..schemas import RoleChangeIn
from ..security import api_error, get_admin
from ..utils import today_kst

log = logging.getLogger(__name__)
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
def run_rpa(background: BackgroundTasks, job: str = Query("deals", pattern="^(deals|public|report|all)$"),
            user: User = Depends(get_admin)):
    if user.email == settings.demo_admin_email:
        raise api_error(status.HTTP_403_FORBIDDEN, "DEMO_READ_ONLY", "체험 관리자 계정은 조회만 가능합니다. (수집 실행 불가)")
    from rpa.run import run_job_isolated  # 지연 import (RPA 의존성)

    background.add_task(run_job_isolated, job)
    return {"job": job, "status": "ACCEPTED"}


# ---------------------------------------------------------------- 회원 권한 관리
def _is_demo_admin(user: User) -> bool:
    return user.email == settings.demo_admin_email


def _mask_email(email: str) -> str:
    """체험 관리자(누구나 로그인 가능)에게는 실제 회원 이메일을 가려서 보여 준다."""
    local, _, domain = email.partition("@")
    return f"{local[:2]}{'*' * max(len(local) - 2, 2)}@{domain}"


def _protected_reason(target: User, actor: User) -> str | None:
    if target.id == actor.id:
        return "본인 권한은 변경할 수 없습니다."
    if target.email in {settings.demo_admin_email, settings.demo_email}:
        return "체험 계정 권한은 변경할 수 없습니다."
    if target.email == (settings.admin_email or "").lower():
        return "기본 관리자(ADMIN_EMAIL) 권한은 변경할 수 없습니다."
    return None


def _user_row(u: User, actor: User) -> dict:
    return {"id": u.id, "name": u.name, "email": _mask_email(u.email) if _is_demo_admin(actor) else u.email,
            "role": u.role, "created_at": u.created_at, "locked": _protected_reason(u, actor)}


@router.get("/users", summary="회원 목록(권한 관리)")
def list_users(q: str = Query("", max_length=100), role: str = Query("", pattern="^(|USER|ADMIN)$"),
               page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               user: User = Depends(get_admin), db: Session = Depends(get_db)):
    stmt = select(User)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), User.name.like(f"%{q.strip()}%")))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.role.asc(), User.created_at.desc(), User.id.desc())
                      .offset((page - 1) * size).limit(size)).all()
    admins = db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN", User.email != settings.demo_admin_email))
    return {"total": total, "page": page, "size": size, "admin_count": admins, "read_only": _is_demo_admin(user),
            "items": [_user_row(u, user) for u in rows]}


@router.patch("/users/{user_id}/role", summary="회원 권한 변경 (USER ↔ ADMIN)")
def change_role(user_id: int, body: RoleChangeIn, user: User = Depends(get_admin), db: Session = Depends(get_db)):
    if _is_demo_admin(user):
        raise api_error(status.HTTP_403_FORBIDDEN, "DEMO_READ_ONLY", "체험 관리자 계정은 조회만 가능합니다. (권한 변경 불가)")
    target = db.get(User, user_id)
    if target is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "회원을 찾을 수 없습니다.")
    if reason := _protected_reason(target, user):
        raise api_error(status.HTTP_409_CONFLICT, "ROLE_LOCKED", reason)
    if target.role != body.role:
        log.info("권한 변경: %s %s → %s (변경자 %s)", target.email, target.role, body.role, user.email)
        target.role = body.role
        db.commit()
        db.refresh(target)
    return _user_row(target, user)

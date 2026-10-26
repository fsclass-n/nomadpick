"""초기 데이터 - 여행사·공항 코드, 관리자/데모 계정."""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..constants import AGENCIES, AIRPORTS
from ..models import Agency, Airport, User, UserPreference
from ..security import hash_password

log = logging.getLogger(__name__)


def seed_reference_data(db: Session) -> None:
    for a in AGENCIES:
        if db.get(Agency, a["id"]) is None:
            db.add(Agency(**a, robots_checked_at=date(2026, 11, 5), is_active=True))
    for ap in AIRPORTS:
        if db.get(Airport, ap["airport_id"]) is None:
            db.add(Airport(**ap))
    _ensure_user(db, settings.admin_email, settings.admin_password, "관리자", "ADMIN")
    demo = _ensure_user(db, settings.demo_email, settings.demo_password, "데모 사용자", "USER")
    if demo is not None and demo.preference is None:
        db.add(UserPreference(user_id=demo.id, regions=["동남아", "일본"], budget_min=300000, budget_max=1000000,
                              depart_months=[], nights_min=2, nights_max=4, theme="휴양", companion="친구"))
    db.commit()


def _ensure_user(db: Session, email: str, password: str, name: str, role: str) -> User | None:
    if not email or not password:
        return None
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        user = User(email=email.lower(), password_hash=hash_password(password), name=name, role=role)
        db.add(user)
        db.flush()
        log.info("초기 계정 생성: %s (%s)", email, role)
    return user

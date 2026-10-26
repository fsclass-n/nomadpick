from datetime import date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    """DB 저장용 KST naive datetime."""
    return datetime.now(KST).replace(tzinfo=None, microsecond=0)


def today_kst() -> date:
    return now_kst().date()


def to_kst_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(KST).replace(tzinfo=None)
    return dt.replace(microsecond=0)

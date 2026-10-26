from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserPreference
from ..schemas import PreferenceIn, PreferenceOut
from ..security import get_current_user

router = APIRouter(tags=["선호 설정"])


@router.get("/preferences", response_model=PreferenceOut | None, summary="선호 설정 조회")
def get_preferences(user: User = Depends(get_current_user)):
    return user.preference


@router.put("/preferences", response_model=PreferenceOut, summary="선호 설정 저장")
def put_preferences(body: PreferenceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = body.model_dump()
    if data["budget_min"] and data["budget_max"] and data["budget_min"] > data["budget_max"]:
        data["budget_min"], data["budget_max"] = data["budget_max"], data["budget_min"]
    if data["nights_min"] is not None and data["nights_max"] is not None and data["nights_min"] > data["nights_max"]:
        data["nights_min"], data["nights_max"] = data["nights_max"], data["nights_min"]
    pref = user.preference or UserPreference(user_id=user.id)
    for k, v in data.items():
        setattr(pref, k, v)
    db.add(pref)
    db.commit()
    return pref

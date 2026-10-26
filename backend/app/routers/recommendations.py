from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import get_current_user
from ..services.excel import recommendations_to_xlsx
from ..services.recommend import recommend

router = APIRouter(tags=["추천"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/recommendations", summary="맞춤 추천 Top 10")
def get_recommendations(limit: int = Query(10, ge=1, le=30), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recommend(db, user.preference, limit)


@router.get("/recommendations/excel", summary="추천 결과 엑셀 다운로드")
def recommendations_excel(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = recommendations_to_xlsx(recommend(db, user.preference, 10), user.name)
    filename = f"nomadpick_추천_{datetime.now():%Y%m%d}.xlsx"
    return Response(content=data, media_type=XLSX,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})

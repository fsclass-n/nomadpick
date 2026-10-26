"""RPA 수신 API - X-RPA-KEY 인증 (사용자 JWT 와 분리)."""
import base64

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import RpaAirportsIn, RpaFlightsIn, RpaLogIn, RpaProductsBulkIn, RpaReportIn
from ..security import api_error, verify_rpa_key
from ..services import ingest

router = APIRouter(prefix="/rpa", tags=["RPA"], dependencies=[Depends(verify_rpa_key)])


@router.post("/products/bulk", summary="정제된 상품 일괄 upsert + 가격 스냅샷")
def products_bulk(body: RpaProductsBulkIn, db: Session = Depends(get_db)):
    try:
        return ingest.upsert_products(db, body.agency_code, body.collected_at, body.source,
                                      [i.model_dump() for i in body.items])
    except ValueError as e:
        raise api_error(status.HTTP_400_BAD_REQUEST, "INVALID_AGENCY", str(e))


@router.put("/flights", summary="국토교통부 국내선 운항정보 갱신")
def put_flights(body: RpaFlightsIn, db: Session = Depends(get_db)):
    return ingest.upsert_flights(db, [i.model_dump() for i in body.items], body.source)


@router.put("/airports", summary="국토교통부 공항 목록 갱신")
def put_airports(body: RpaAirportsIn, db: Session = Depends(get_db)):
    return ingest.upsert_airports(db, [i.model_dump() for i in body.items])


@router.post("/logs", status_code=status.HTTP_201_CREATED, summary="수집 실행 로그 등록")
def post_log(body: RpaLogIn, db: Session = Depends(get_db)):
    return {"id": ingest.add_log(db, body.model_dump()).id}


@router.post("/reports", status_code=status.HTTP_201_CREATED, summary="일일 엑셀 리포트 업로드")
def post_report(body: RpaReportIn, db: Session = Depends(get_db)):
    row = ingest.save_report(db, body.report_date, body.file_name, base64.b64decode(body.file_base64),
                             body.chart_html, body.summary)
    return {"id": row.id, "report_date": row.report_date.isoformat()}

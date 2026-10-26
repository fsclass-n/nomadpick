"""프런트엔드 오프라인 데모 데이터 생성 (frontend/data/sample-products.json).

1단계(Netlify 단독 배포) 또는 Render 슬립 중에도 화면을 확인할 수 있도록,
TiDB(DATABASE_URL)에 적재된 현재 활성 상품·가격 이력·국내선 항공편을 JSON 스냅샷으로 내보낸다.

    python -m rpa.export_sample
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from backend.app.constants import AGENCIES, COMPANIONS, REGIONS, THEMES
    from backend.app.database import SessionLocal
    from backend.app.services.products import active_products_query, flights_for, price_history, serialize

    with SessionLocal() as db:
        products = db.scalars(active_products_query()).unique().all()
        if not products:
            raise SystemExit("활성 상품이 없습니다. 먼저 python -m rpa.run all 로 수집하세요.")
        out = {
            "meta": {"regions": REGIONS, "themes": THEMES, "companions": COMPANIONS, "total": len(products),
                     "collected_at": max(p.last_seen_at for p in products).isoformat(),
                     "agencies": [{**a, "count": sum(p.agency_id == a["id"] for p in products)} for a in AGENCIES]},
            "products": [{**serialize(p), "agency_id": p.agency_id, "is_active": True} for p in products],
            "prices": {p.id: price_history(db, p.id, 30) for p in products},
            "flights": {p.id: f for p in products if (f := flights_for(db, p))},
        }
    target = ROOT / "frontend" / "data" / "sample-products.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{target} - 상품 {len(out['products'])}건")


if __name__ == "__main__":
    main()

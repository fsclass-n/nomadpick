from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Favorite, TravelProduct, User
from ..schemas import FavoriteIn
from ..security import api_error, get_current_user
from ..services.products import serialize

router = APIRouter(tags=["관심 상품"])


@router.get("/favorites", summary="관심 상품 목록")
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favs = db.scalars(select(Favorite).options(joinedload(Favorite.product).joinedload(TravelProduct.agency))
                      .where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())).all()
    return [{**serialize(f.product), "saved_price": f.saved_price, "is_active": f.product.is_active,
             "price_dropped": f.product.price < f.saved_price, "price_diff": f.product.price - f.saved_price,
             "favorited_at": f.created_at.isoformat() if f.created_at else None} for f in favs]


@router.post("/favorites", status_code=status.HTTP_201_CREATED, summary="관심 상품 등록")
def add_favorite(body: FavoriteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(TravelProduct, body.product_id)
    if product is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", "상품을 찾을 수 없습니다.")
    fav = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product.id))
    if fav is None:
        fav = Favorite(user_id=user.id, product_id=product.id, saved_price=product.price)
        db.add(fav)
        db.commit()
    return {"product_id": product.id, "saved_price": fav.saved_price}


@router.delete("/favorites/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="관심 상품 해제")
def delete_favorite(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fav = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id))
    if fav:
        db.delete(fav)
        db.commit()

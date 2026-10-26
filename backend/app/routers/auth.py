from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, SignupIn, TokenOut, UserOut
from ..security import api_error, create_token, get_current_user, hash_password, verify_password

router = APIRouter(tags=["인증·회원"])


def _token_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_token(user), expires_in=settings.jwt_expire_minutes * 60,
                    user=UserOut.model_validate(user), has_preference=user.preference is not None)


@router.post("/auth/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED, summary="회원가입")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise api_error(status.HTTP_409_CONFLICT, "EMAIL_EXISTS", "이미 가입된 이메일입니다.")
    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/auth/login", response_model=TokenOut, summary="로그인(JWT 발급)")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")
    return _token_response(user)


@router.get("/users/me", response_model=UserOut, summary="내 정보")
def me(user: User = Depends(get_current_user)):
    return user

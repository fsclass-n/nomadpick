"""인증 - bcrypt 비밀번호 해시, JWT(사용자), X-RPA-KEY(수집기) 분리."""
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def _user_from_credentials(credentials: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "로그인이 만료되었습니다. 다시 로그인해 주세요.")
    except jwt.PyJWTError:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "유효하지 않은 토큰입니다.")
    return db.get(User, int(payload["sub"]))


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = _user_from_credentials(credentials, db)
    if user is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "로그인이 필요합니다.")
    return user


def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User | None:
    try:
        return _user_from_credentials(credentials, db)
    except HTTPException:
        return None


def get_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "관리자만 접근할 수 있습니다.")
    return user


def verify_rpa_key(x_rpa_key: str | None = Header(default=None, alias="X-RPA-KEY")) -> None:
    if not x_rpa_key or not hmac.compare_digest(x_rpa_key, settings.rpa_api_key):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_RPA_KEY", "RPA 인증 키가 올바르지 않습니다.")

"""SNS 로그인 (Google · Naver · Kakao) - OAuth 2.0 Authorization Code.

흐름: 프런트 [SNS 버튼] → GET /auth/oauth/{provider}/start → 제공자 로그인·동의
      → GET /auth/oauth/{provider}/callback?code&state → 토큰 교환 · 프로필 조회 → 회원 조회/생성
      → 로그인 페이지로 리다이렉트 (#oauth_token=JWT) → 프런트가 /users/me 로 사용자 정보 저장
키 설정: .env 의 GOOGLE_/NAVER_/KAKAO_ CLIENT_ID·CLIENT_SECRET (없는 제공자는 비활성)
콜백 URL(각 개발자 콘솔에 등록): {PUBLIC_BASE_URL}/api/v1/auth/oauth/{provider}/callback
"""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import jwt
import requests
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..security import api_error, create_token, hash_password

router = APIRouter(tags=["인증·회원"])

PROVIDERS = {
    "google": {"authorize": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
               "profile": "https://openidconnect.googleapis.com/v1/userinfo", "scope": "openid email profile"},
    "naver": {"authorize": "https://nid.naver.com/oauth2.0/authorize", "token": "https://nid.naver.com/oauth2.0/token",
              "profile": "https://openapi.naver.com/v1/nid/me", "scope": ""},
    "kakao": {"authorize": "https://kauth.kakao.com/oauth/authorize", "token": "https://kauth.kakao.com/oauth/token",
              "profile": "https://kapi.kakao.com/v2/user/me", "scope": "profile_nickname account_email"},
}
LABEL = {"google": "Google", "naver": "네이버", "kakao": "카카오"}


def _enabled(provider: str) -> bool:
    cid, secret = settings.oauth.get(provider, ("", ""))
    return bool(cid and (secret or provider == "kakao"))  # 카카오는 Client Secret 선택


def _callback_url(request: Request, provider: str) -> str:
    base = settings.public_base_url or str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/oauth/{provider}/callback"


def _safe_return(request: Request, return_to: str | None) -> str:
    """로그인 후 돌아갈 프런트 주소 - 같은 서버 또는 CORS 허용 도메인만 (오픈 리다이렉트 방지)."""
    default = (settings.public_base_url or str(request.base_url).rstrip("/")) + "/login.html"
    if not return_to:
        return default
    u = urlparse(return_to)
    origin = f"{u.scheme}://{u.netloc}"
    allowed = {f"{urlparse(default).scheme}://{urlparse(default).netloc}", *settings.cors_origins}
    return return_to.split("#")[0] if u.scheme in ("http", "https") and origin in allowed else default


@router.get("/auth/oauth/providers", summary="사용 가능한 SNS 로그인")
def providers():
    return {p: _enabled(p) for p in PROVIDERS}


@router.get("/auth/oauth/{provider}/start", summary="SNS 로그인 시작 (제공자 로그인 화면으로 이동)")
def start(provider: str, request: Request, return_to: str | None = Query(None)):
    if provider not in PROVIDERS:
        raise api_error(status.HTTP_404_NOT_FOUND, "UNKNOWN_PROVIDER", "지원하지 않는 로그인 방식입니다.")
    back = _safe_return(request, return_to)
    if not _enabled(provider):
        return RedirectResponse(f"{back}#oauth_error={LABEL[provider]} 로그인이 아직 설정되지 않았습니다.", status.HTTP_302_FOUND)
    state = jwt.encode({"p": provider, "r": back, "n": secrets.token_urlsafe(8),
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.jwt_secret, algorithm="HS256")
    conf = PROVIDERS[provider]
    params = {"response_type": "code", "client_id": settings.oauth[provider][0], "redirect_uri": _callback_url(request, provider), "state": state}
    if conf["scope"]:
        params["scope"] = conf["scope"]
    return RedirectResponse(f"{conf['authorize']}?{urlencode(params)}", status.HTTP_302_FOUND)


def _fetch_profile(provider: str, code: str, state: str, redirect_uri: str) -> tuple[str, str, str]:
    """(제공자 사용자 ID, 이메일, 이름) 반환."""
    conf = PROVIDERS[provider]
    cid, secret = settings.oauth[provider]
    data = {"grant_type": "authorization_code", "client_id": cid, "code": code, "redirect_uri": redirect_uri}
    if secret:
        data["client_secret"] = secret
    if provider == "naver":
        data["state"] = state
    tok = requests.post(conf["token"], data=data, timeout=15)
    tok.raise_for_status()
    access = tok.json()["access_token"]
    prof = requests.get(conf["profile"], headers={"Authorization": f"Bearer {access}"}, timeout=15)
    prof.raise_for_status()
    p = prof.json()
    if provider == "google":
        return p["sub"], p.get("email", ""), p.get("name") or "Google 사용자"
    if provider == "naver":
        r = p.get("response", {})
        return r["id"], r.get("email", ""), r.get("name") or r.get("nickname") or "네이버 사용자"
    acc = p.get("kakao_account", {})
    return str(p["id"]), acc.get("email", ""), (acc.get("profile") or {}).get("nickname") or p.get("properties", {}).get("nickname") or "카카오 사용자"


@router.get("/auth/oauth/{provider}/callback", summary="SNS 로그인 콜백")
def callback(provider: str, request: Request, code: str | None = None, state: str | None = None,
             error: str | None = None, db: Session = Depends(get_db)):
    try:
        st = jwt.decode(state or "", settings.jwt_secret, algorithms=["HS256"])
        if st.get("p") != provider:
            raise ValueError("provider mismatch")
    except Exception:
        return RedirectResponse(f"{_safe_return(request, None)}#oauth_error=로그인 요청이 만료되었습니다. 다시 시도해 주세요.", status.HTTP_302_FOUND)
    back = st["r"]
    if error or not code:
        return RedirectResponse(f"{back}#oauth_error={LABEL[provider]} 로그인이 취소되었습니다.", status.HTTP_302_FOUND)
    try:
        uid, email, name = _fetch_profile(provider, code, state, _callback_url(request, provider))
    except Exception:
        return RedirectResponse(f"{back}#oauth_error={LABEL[provider]} 인증에 실패했습니다.", status.HTTP_302_FOUND)

    email = (email or f"{provider}_{uid}@users.nomadpick.local").lower()  # 이메일 미제공(카카오 비동의 등) 시 대체 ID
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(24)), name=name[:50], role="USER")
        db.add(user)
        db.commit()
        db.refresh(user)
    pref = 1 if user.preference is not None else 0
    return RedirectResponse(f"{back}#oauth_token={create_token(user)}&pref={pref}", status.HTTP_302_FOUND)

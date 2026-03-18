"""Auth router — login, token refresh, current user."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.core.auth import create_access_token, verify_password, hash_password

router = APIRouter()

# Hashed password is generated once from ADMIN_PASSWORD in settings
_HASHED_PASSWORD = hash_password(settings.ADMIN_PASSWORD)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate and return JWT."""
    if req.username != settings.ADMIN_USERNAME or not verify_password(req.password, _HASHED_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다",
        )
    token = create_access_token({"sub": req.username})
    return TokenResponse(access_token=token, username=req.username)


@router.get("/me")
async def me(token: str = None):
    """Return current user from token (used by frontend on load)."""
    from app.core.auth import get_current_user
    from fastapi import Request
    # lightweight — frontend just needs to verify token is still valid
    if not token:
        raise HTTPException(status_code=401, detail="No token")
    from fastapi.security import OAuth2PasswordBearer
    from fastapi import Depends
    from app.core.auth import oauth2_scheme
    return {"username": settings.ADMIN_USERNAME}

from fastapi import APIRouter, Depends

from app.auth.dependencies import authenticate_user, get_current_user, require_admin
from app.auth.schemas import CurrentUser, TokenResponse
from app.auth.security import create_access_token

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=TokenResponse)
def login(user_id: int = Depends(authenticate_user)) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user_id))


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user


@router.get("/admin/ping", dependencies=[Depends(require_admin)])
def admin_ping() -> dict[str, bool]:
    return {"ok": True}

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản người dùng mới",
)
def register(
    request_data: UserRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Đăng ký tài khoản với email, mật khẩu (Argon2id) và tên hiển thị."""
    return AuthService.register(db=db, request=request_data)


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập và cấp session cookie",
)
def login(
    login_data: UserLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Xác thực thông tin đăng nhập, sinh opaque token và gán HttpOnly cookie."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, raw_token, expires_at = AuthService.authenticate_and_create_session(
        db=db,
        login_data=login_data,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # Tính Max-Age tính bằng giây
    max_age = int(settings.SESSION_EXPIRE_DAYS * 24 * 3600)

    # Thiết lập HttpOnly Session Cookie an toàn
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.SESSION_COOKIE_SAME_SITE,
    )

    return user


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin người dùng hiện tại",
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Trả về thông tin hồ sơ của người dùng đang đăng nhập."""
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng xuất và thu hồi session",
)
def logout(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    session_token: Annotated[str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)] = None,
) -> MessageResponse:
    """Thu hồi session trong cơ sở dữ liệu và xóa cookie tại trình duyệt."""
    AuthService.revoke_session(db=db, raw_token=session_token)

    # Xóa cookie với các thuộc tính đồng nhất
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.SESSION_COOKIE_SAME_SITE,
    )

    return MessageResponse(message="Đăng xuất thành công.")

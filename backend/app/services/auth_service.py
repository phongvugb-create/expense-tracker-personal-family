import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest

logger = logging.getLogger(__name__)


class AuthService:
    """Service xử lý nghiệp vụ đăng ký, xác thực, quản lý và thu hồi phiên đăng nhập."""

    @staticmethod
    def register(db: Session, request: UserRegisterRequest) -> User:
        """Đăng ký tài khoản người dùng mới vào PostgreSQL."""
        normalized_email = request.email.strip().lower()

        # Kiểm tra trước để trả thông báo người dùng thân thiện
        existing_user = db.scalar(
            select(User).where(User.email == normalized_email)
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được đăng ký trong hệ thống.",
            )

        # Băm mật khẩu bằng Argon2id
        hashed_pw = hash_password(request.password)

        new_user = User(
            email=normalized_email,
            password_hash=hashed_pw,
            display_name=request.display_name.strip(),
            is_active=True,
        )

        db.add(new_user)
        try:
            db.commit()
            db.refresh(new_user)
            return new_user
        except IntegrityError as exc:
            db.rollback()
            # Xử lý an toàn race-condition nếu 2 request đăng ký cùng email cùng lúc
            logger.warning("IntegrityError khi đăng ký tài khoản email %s: %s", normalized_email, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được đăng ký trong hệ thống.",
            ) from exc

    @staticmethod
    def authenticate_and_create_session(
        db: Session,
        login_data: UserLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, datetime]:
        """
        Xác thực thông tin đăng nhập và tạo phiên làm việc mới.
        Trả về: (User, raw_token, expires_at)
        """
        normalized_email = login_data.email.strip().lower()

        user = db.scalar(
            select(User).where(User.email == normalized_email)
        )

        # Sử dụng thông báo chung khi sai tài khoản hoặc mật khẩu để tránh User Enumeration
        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
        )

        if user is None:
            # Ngăn timing attack bằng cách verify với dummy hash nếu user không tồn tại
            verify_password(
                login_data.password,
                "$argon2id$v=19$m=65536,t=3,p=4$dummyhashdummysalt$dummyverificationresultfailed"
            )
            raise generic_error

        # Kiểm tra trạng thái tài khoản (khóa hoặc xóa mềm)
        if not user.is_active or user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa hoặc không còn hoạt động.",
            )

        if not verify_password(login_data.password, user.password_hash):
            raise generic_error

        # Sinh token ngẫu nhiên bảo mật cao và tính hash SHA-256
        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=settings.SESSION_EXPIRE_DAYS)

        session_record = AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            last_used_at=now,
        )

        db.add(session_record)
        db.commit()

        return user, raw_token, expires_at

    @staticmethod
    def get_user_from_token(db: Session, raw_token: str) -> User:
        """
        Tra cứu phiên đăng nhập từ raw_token và trả về User hợp lệ.
        Kiểm tra: tính hợp lệ của session (chưa thu hồi, chưa hết hạn) và user (active, chưa xóa mềm).
        """
        token_hash = hash_session_token(raw_token)

        session_record = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )

        if session_record is None or not session_record.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            )

        user = session_record.user
        if user is None or not user.is_active or user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản không còn hoạt động hoặc đã bị vô hiệu hóa.",
            )

        # Cập nhật thời điểm sử dụng phiên làm việc gần nhất
        session_record.last_used_at = datetime.now(UTC)
        db.commit()

        return user

    @staticmethod
    def revoke_session(db: Session, raw_token: str | None) -> None:
        """Thu hồi phiên đăng nhập hiện tại bằng cách gán revoked_at."""
        if not raw_token:
            return

        token_hash = hash_session_token(raw_token)
        session_record = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )

        if session_record is not None and not session_record.is_revoked:
            session_record.revoked_at = datetime.now(UTC)
            db.commit()

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Cấu hình hasher Argon2id chuẩn bảo mật cao
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng thuật toán Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu dạng rõ với chuỗi băm Argon2id."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def generate_session_token() -> str:
    """Sinh chuỗi opaque session token ngẫu nhiên bảo mật cao (256-bit entropy)."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Tính chuỗi băm SHA-256 của token để lưu trữ an toàn trong database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

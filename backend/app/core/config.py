from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# Đường dẫn thư mục gốc dự án chứa file .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent  # Thư mục gốc dự án


class Settings(BaseSettings):
    """Cấu hình ứng dụng tải từ biến môi trường và file .env."""

    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_ROOT / ".env"),
            str(BASE_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General app settings
    PROJECT_NAME: str = "Expense Tracker API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Auth & Session cookie settings
    SESSION_COOKIE_NAME: str = "session_token"
    SESSION_EXPIRE_DAYS: int = 7
    SESSION_COOKIE_SECURE: bool | None = None  # None: tự động True nếu production, False nếu development
    SESSION_COOKIE_SAME_SITE: str = "lax"

    # Family & Invitation settings
    FAMILY_INVITATION_EXPIRE_DAYS: int = 7
    RETURN_INVITATION_TOKEN_IN_DEV: bool = True  # Cho phép trả token thô trong môi trường dev/demo để copy

    # CORS settings (Origins được phép truy cập từ frontend kèm cookie)
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def is_cookie_secure(self) -> bool:
        """Xác định cờ Secure của cookie dựa trên môi trường."""
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.ENVIRONMENT.lower() == "production"

    # Database settings
    # Mặc định khi chạy native trên Windows: 127.0.0.1:5434
    # Khi chạy trong Docker Compose: có thể ghi đè bằng POSTGRES_HOST=db, POSTGRES_PORT=5432
    POSTGRES_HOST: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("POSTGRES_HOST", "POSTGRES_SERVER"),
    )
    POSTGRES_PORT: int = 5434
    POSTGRES_DB: str = "expense_tracker"
    POSTGRES_USER: str = "expense_app"
    POSTGRES_PASSWORD: str = ""

    # Connection pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    @property
    def database_url(self) -> URL:
        """Tạo đối tượng URL kết nối an toàn cho SQLAlchemy với psycopg 3 driver."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    @property
    def safe_database_uri(self) -> str:
        """Chuỗi URI kết nối đã ẩn mật khẩu an toàn phục vụ chẩn đoán và logging."""
        return self.database_url.render_as_string(hide_password=True)


settings = Settings()

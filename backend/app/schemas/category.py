import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# Category Request Schemas
# ==============================================================================
class CategoryCreateRequest(BaseModel):
    """Schema tạo danh mục thu/chi mới."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên danh mục (ví dụ: Ăn uống, Lương, Mua sắm...)",
    )
    type: Literal["income", "expense"] = Field(
        ...,
        description="Loại danh mục: 'income' (thu nhập) hoặc 'expense' (chi tiêu)",
    )
    scope: Literal["personal", "family"] = Field(
        ...,
        description="Phạm vi sở hữu: 'personal' (cá nhân) hoặc 'family' (gia đình). Người dùng thông thường không được tạo scope 'system'.",
    )
    family_id: uuid.UUID | None = Field(
        default=None,
        description="ID nhóm gia đình (bắt buộc khi scope='family', cấm khi scope='personal')",
    )
    parent_id: uuid.UUID | None = Field(
        default=None,
        description="ID danh mục cha nếu muốn tạo danh mục con (phải cùng type và tương thích phạm vi)",
    )
    icon: str | None = Field(
        default=None,
        max_length=50,
        description="Tên icon nhận diện (ví dụ: 'utensils', 'car', 'home' hoặc Lucide icon name)",
    )
    color: str | None = Field(
        default=None,
        max_length=20,
        description="Mã màu HEX hoặc CSS (ví dụ: '#3B82F6', '#EF4444')",
    )


class CategoryUpdateRequest(BaseModel):
    """Schema cập nhật danh mục thu/chi."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Tên mới của danh mục",
    )
    icon: str | None = Field(
        default=None,
        max_length=50,
        description="Tên icon nhận diện mới",
    )
    color: str | None = Field(
        default=None,
        max_length=20,
        description="Mã màu HEX hoặc CSS mới",
    )


# ==============================================================================
# Category Response Schema
# ==============================================================================
class CategoryResponse(BaseModel):
    """Schema phản hồi thông tin chi tiết danh mục."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: Literal["income", "expense"]
    scope: Literal["system", "personal", "family"]
    user_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    icon: str | None = None
    color: str | None = None
    is_default: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

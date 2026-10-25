import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách danh mục thu/chi được phép truy cập",
)
def get_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    type: Annotated[
        Literal["income", "expense"] | None,
        Query(description="Lọc theo loại: 'income' (thu nhập) hoặc 'expense' (chi tiêu)"),
    ] = None,
    scope: Annotated[
        Literal["system", "personal", "family"] | None,
        Query(description="Lọc theo phạm vi: 'system', 'personal' hoặc 'family'"),
    ] = None,
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID nhóm gia đình mà người dùng có quyền"),
    ] = None,
    include_archived: Annotated[
        bool,
        Query(description="Bao gồm cả các danh mục đã lưu trữ hay không"),
    ] = False,
) -> list[CategoryResponse]:
    """
    Trả về danh sách danh mục mà người dùng có quyền xem:
    - Danh mục hệ thống (system) luôn hiển thị.
    - Danh mục cá nhân (personal) chỉ hiển thị của chính mình.
    - Danh mục gia đình (family) chỉ hiển thị khi có quyền trong nhóm tương ứng.
    """
    return CategoryService.get_categories(
        db=db,
        current_user=current_user,
        type_=type,
        scope=scope,
        family_id=family_id,
        include_archived=include_archived,
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo danh mục thu/chi mới",
)
def create_category(
    request: CategoryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Tạo danh mục cá nhân hoặc gia đình mới."""
    return CategoryService.create_category(
        db=db, current_user=current_user, request=request
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết danh mục thu/chi",
)
def get_category_detail(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Xem thông tin chi tiết một danh mục nếu có quyền truy cập."""
    return CategoryService.get_category_detail(
        db=db, category_id=category_id, current_user=current_user
    )


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Chỉnh sửa danh mục thu/chi",
)
def update_category(
    category_id: uuid.UUID,
    request: CategoryUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Chỉnh sửa thông tin danh mục (tên, icon, color)."""
    return CategoryService.update_category(
        db=db,
        category_id=category_id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/{category_id}/archive",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu trữ danh mục thu/chi",
)
def archive_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Lưu trữ danh mục để ẩn khỏi danh sách lựa chọn thu/chi mới."""
    return CategoryService.set_archive_status(
        db=db, category_id=category_id, current_user=current_user, archive=True
    )


@router.post(
    "/{category_id}/restore",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Khôi phục danh mục thu/chi đã lưu trữ",
)
def restore_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Khôi phục danh mục về trạng thái hoạt động."""
    return CategoryService.set_archive_status(
        db=db, category_id=category_id, current_user=current_user, archive=False
    )

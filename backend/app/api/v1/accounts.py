from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get(
    "",
    response_model=list[AccountResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách ví tài khoản được phép truy cập",
)
def get_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[
        Literal["personal", "family"] | None,
        Query(description="Lọc theo scope: personal hoặc family"),
    ] = None,
    family_id: Annotated[
        UUID | None,
        Query(description="Lọc ví của nhóm gia đình cụ thể"),
    ] = None,
    include_archived: Annotated[
        bool,
        Query(description="Bao gồm các ví đã lưu trữ (mặc định false)"),
    ] = False,
) -> list[AccountResponse]:
    """Trả về danh sách các ví mà người dùng có quyền xem kèm số dư tính toán hiện tại."""
    return AccountService.get_accessible_accounts(
        db=db,
        current_user=current_user,
        scope=scope,
        family_id=family_id,
        include_archived=include_archived,
    )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo ví tài khoản mới",
)
def create_account(
    request: AccountCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Tạo ví cá nhân hoặc ví gia đình (kiểm tra quyền với nhóm gia đình tương ứng)."""
    return AccountService.create_account(
        db=db,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết ví tài khoản",
)
def get_account_detail(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Xem chi tiết thông tin ví và số dư khả dụng hiện tại."""
    return AccountService.get_account_detail(
        db=db,
        account_id=account_id,
        current_user=current_user,
    )


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Chỉnh sửa thông tin ví",
)
def update_account(
    account_id: UUID,
    request: AccountUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Chỉnh sửa thông tin ví được phép (tên ví, loại ví)."""
    return AccountService.update_account(
        db=db,
        account_id=account_id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/{account_id}/archive",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu trữ ví tài khoản",
)
def archive_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Lưu trữ ví (is_archived = true)."""
    return AccountService.set_archive_status(
        db=db,
        account_id=account_id,
        current_user=current_user,
        archive=True,
    )


@router.post(
    "/{account_id}/restore",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Khôi phục ví tài khoản đã lưu trữ",
)
def restore_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Khôi phục ví đã lưu trữ (is_archived = false)."""
    return AccountService.set_archive_status(
        db=db,
        account_id=account_id,
        current_user=current_user,
        archive=False,
    )

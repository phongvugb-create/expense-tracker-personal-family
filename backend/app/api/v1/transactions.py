import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionResponse,
    TransactionUpdateRequest,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "",
    response_model=list[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách giao dịch thu/chi",
)
def get_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID ví tài chính"),
    ] = None,
    category_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID danh mục thu chi"),
    ] = None,
    type: Annotated[
        Literal["income", "expense"] | None,
        Query(description="Lọc theo loại giao dịch: 'income' hoặc 'expense'"),
    ] = None,
    date_from: Annotated[
        datetime | None,
        Query(description="Thời điểm bắt đầu (occurred_at >= date_from)"),
    ] = None,
    date_to: Annotated[
        datetime | None,
        Query(description="Thời điểm kết thúc (occurred_at <= date_to)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Số lượng bản ghi tối đa trả về"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Vị trí bản ghi bắt đầu lấy"),
    ] = 0,
) -> list[TransactionResponse]:
    """Lấy danh sách các giao dịch thu chi mà người dùng có quyền xem."""
    return TransactionService.get_transactions(
        db=db,
        current_user=current_user,
        account_id=account_id,
        category_id=category_id,
        type_=type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo giao dịch thu/chi mới",
)
def create_transaction(
    request: TransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransactionResponse:
    """Tạo giao dịch thu hoặc chi trên ví cá nhân hoặc ví gia đình."""
    return TransactionService.create_transaction(
        db=db, current_user=current_user, request=request
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết giao dịch thu/chi",
)
def get_transaction_detail(
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransactionResponse:
    """Xem thông tin chi tiết của một giao dịch nếu có quyền truy cập."""
    return TransactionService.get_transaction_detail(
        db=db, transaction_id=transaction_id, current_user=current_user
    )


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Chỉnh sửa giao dịch thu/chi",
)
def update_transaction(
    transaction_id: uuid.UUID,
    request: TransactionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransactionResponse:
    """Cập nhật giao dịch thu/chi (số tiền, danh mục, loại, ghi chú, ngày phát sinh)."""
    return TransactionService.update_transaction(
        db=db,
        transaction_id=transaction_id,
        current_user=current_user,
        request=request,
    )


@router.delete(
    "/{transaction_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Xóa mềm giao dịch thu/chi",
)
def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Đánh dấu xóa mềm giao dịch (cập nhật deleted_at, tự động loại trừ khỏi số dư ví)."""
    return TransactionService.soft_delete_transaction(
        db=db, transaction_id=transaction_id, current_user=current_user
    )

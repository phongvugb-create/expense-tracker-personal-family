import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreateRequest,
    RecurringTransactionGenerateResponse,
    RecurringTransactionResponse,
    RecurringTransactionUpdateRequest,
)
from app.services.recurring_transaction_service import RecurringTransactionService

recurring_router = APIRouter(prefix="/recurring-transactions", tags=["Recurring Transactions"])


@recurring_router.get(
    "",
    response_model=list[RecurringTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách các quy tắc thu/chi định kỳ",
)
def get_recurring_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[
        Literal["all", "personal", "family"],
        Query(description="Phạm vi: 'all', 'personal' hoặc 'family'"),
    ] = "all",
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="ID nhóm gia đình (tùy chọn)"),
    ] = None,
    type: Annotated[
        Literal["income", "expense"] | None,
        Query(description="Loại giao dịch: 'income' hoặc 'expense'"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Lọc theo trạng thái hoạt động"),
    ] = None,
    include_archived: Annotated[
        bool,
        Query(description="Bao gồm các quy tắc đã lưu trữ"),
    ] = False,
    due_before: Annotated[
        date | None,
        Query(description="Lọc các quy tắc có ngày đến hạn <= due_before"),
    ] = None,
) -> list[RecurringTransactionResponse]:
    return RecurringTransactionService.get_list(
        db=db,
        user=current_user,
        scope=scope,
        family_id=family_id,
        type_=type,
        is_active=is_active,
        include_archived=include_archived,
        due_before=due_before,
    )


@recurring_router.post(
    "",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo quy tắc thu hoặc chi định kỳ mới",
)
def create_recurring_transaction(
    payload: RecurringTransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.create(db=db, user=current_user, payload=payload)


@recurring_router.get(
    "/{id}",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết một quy tắc định kỳ",
)
def get_recurring_transaction(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.get_by_id(db=db, user=current_user, rule_id=id)


@recurring_router.patch(
    "/{id}",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật quy tắc định kỳ",
)
def update_recurring_transaction(
    id: uuid.UUID,
    payload: RecurringTransactionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.update(db=db, user=current_user, rule_id=id, payload=payload)


@recurring_router.post(
    "/{id}/pause",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Tạm dừng quy tắc định kỳ",
)
def pause_recurring_transaction(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.pause(db=db, user=current_user, rule_id=id)


@recurring_router.post(
    "/{id}/resume",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Kích hoạt lại quy tắc định kỳ",
)
def resume_recurring_transaction(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.resume(db=db, user=current_user, rule_id=id)


@recurring_router.post(
    "/{id}/archive",
    response_model=RecurringTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu trữ quy tắc định kỳ",
)
def archive_recurring_transaction(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionResponse:
    return RecurringTransactionService.archive(db=db, user=current_user, rule_id=id)


@recurring_router.post(
    "/{id}/generate",
    response_model=RecurringTransactionGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Chủ động tạo một giao dịch thực tế từ kỳ đến hạn hiện tại",
)
def generate_recurring_transaction(
    id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringTransactionGenerateResponse:
    return RecurringTransactionService.generate_transaction(db=db, user=current_user, rule_id=id)

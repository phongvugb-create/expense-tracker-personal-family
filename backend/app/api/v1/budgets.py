import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetResponse,
    BudgetUpdateRequest,
)
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get(
    "",
    response_model=list[BudgetResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách ngân sách có quyền truy cập",
)
def get_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    scope: Annotated[
        str | None,
        Query(description="Lọc theo phạm vi ngân sách: 'personal' hoặc 'family'"),
    ] = None,
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID nhóm gia đình (yêu cầu là thành viên có quyền)"),
    ] = None,
    category_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID danh mục chi tiêu"),
    ] = None,
    include_archived: Annotated[
        bool,
        Query(description="Bao gồm cả các ngân sách đã lưu trữ"),
    ] = False,
    active_on: Annotated[
        date | None,
        Query(description="Lọc các ngân sách đang có hiệu lực tại ngày này (period_start <= active_on <= period_end)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Số lượng ngân sách tối đa trả về"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Vị trí bắt đầu lấy bản ghi"),
    ] = 0,
) -> list[BudgetResponse]:
    """Liệt kê danh sách các ngân sách chi tiêu kèm tính toán số tiền đã chi và trạng thái cảnh báo theo thời gian thực."""
    return BudgetService.get_budgets(
        db=db,
        current_user=current_user,
        scope=scope,
        family_id=family_id,
        category_id=category_id,
        include_archived=include_archived,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo ngân sách chi tiêu mới",
)
def create_budget(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    req: BudgetCreateRequest,
) -> BudgetResponse:
    """Tạo ngân sách cá nhân hoặc gia đình mới theo danh mục chi tiêu với hạn mức và ngưỡng cảnh báo."""
    return BudgetService.create_budget(
        db=db,
        req=req,
        current_user=current_user,
    )


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết một ngân sách",
)
def get_budget_by_id(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetResponse:
    """Lấy thông tin chi tiết của ngân sách, số tiền đã chi, số tiền còn lại và trạng thái cảnh báo."""
    return BudgetService.get_budget_by_id(
        db=db,
        budget_id=budget_id,
        current_user=current_user,
    )


@router.patch(
    "/{budget_id}",
    response_model=BudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Chỉnh sửa thông tin ngân sách",
)
def update_budget(
    budget_id: uuid.UUID,
    req: BudgetUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetResponse:
    """Cập nhật tên, hạn mức, khoảng thời gian, danh mục hoặc ngưỡng cảnh báo của ngân sách."""
    return BudgetService.update_budget(
        db=db,
        budget_id=budget_id,
        req=req,
        current_user=current_user,
    )


@router.post(
    "/{budget_id}/archive",
    response_model=BudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu trữ ngân sách",
)
def archive_budget(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetResponse:
    """Chuyển ngân sách vào trạng thái lưu trữ mà không xóa lịch sử giao dịch hay bản ghi."""
    return BudgetService.archive_budget(
        db=db,
        budget_id=budget_id,
        current_user=current_user,
    )


@router.post(
    "/{budget_id}/restore",
    response_model=BudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Khôi phục ngân sách từ lưu trữ",
)
def restore_budget(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetResponse:
    """Khôi phục ngân sách đã lưu trữ về trạng thái hoạt động bình thường."""
    return BudgetService.restore_budget(
        db=db,
        budget_id=budget_id,
        current_user=current_user,
    )

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy dữ liệu tổng hợp tài chính cho trang Dashboard",
)
def get_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Năm thống kê (từ 2000 đến 2100)"),
    ] = None,
    month: Annotated[
        int | None,
        Query(ge=1, le=12, description="Tháng thống kê (từ 1 đến 12)"),
    ] = None,
    scope: Annotated[
        Literal["all", "personal", "family"],
        Query(description="Phạm vi thống kê: 'all', 'personal' hoặc 'family'"),
    ] = "all",
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="ID nhóm gia đình cụ thể (yêu cầu quyền truy cập)"),
    ] = None,
) -> DashboardSummaryResponse:
    """
    Trả về toàn bộ dữ liệu tài chính thời gian thực:
    - Số dư khả dụng theo từng loại tiền tệ.
    - Dòng tiền trong kỳ (Thu, Chi, Phí chuyển tiền, Dòng tiền thuần).
    - Xu hướng thu/chi 6 tháng gần nhất cho biểu đồ.
    - Cơ cấu chi tiêu theo danh mục.
    - Giao dịch thu/chi gần đây và các lần chuyển tiền gần nhất.
    - Danh sách ngân sách đang chạm ngưỡng cảnh báo hoặc vượt hạn mức.
    """
    return DashboardService.get_summary(
        db=db,
        current_user=current_user,
        year=year,
        month=month,
        scope=scope,
        family_id=family_id,
    )

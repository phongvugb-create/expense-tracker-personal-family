import urllib.parse
import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import ReportSummaryResponse
from app.services.report_service import ReportService

reports_router = APIRouter()


@reports_router.get(
    "/summary",
    response_model=ReportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Báo cáo tài chính chuyên sâu tổng hợp",
    description="Thống kê dòng tiền, cơ cấu chi tiêu danh mục, hiệu suất ví, xu hướng tháng, top chi tiêu và so sánh kỳ trước.",
)
def get_report_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date, Query(description="Ngày bắt đầu (YYYY-MM-DD)")],
    date_to: Annotated[date, Query(description="Ngày kết thúc (YYYY-MM-DD)")],
    scope: Annotated[
        Literal["all", "personal", "family"],
        Query(description="Phạm vi thống kê: 'all', 'personal' hoặc 'family'"),
    ] = "all",
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="ID nhóm gia đình (tùy chọn khi lọc dữ liệu gia đình)"),
    ] = None,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="ID ví tài khoản cụ thể (tùy chọn)"),
    ] = None,
) -> ReportSummaryResponse:
    return ReportService.get_summary(
        db=db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        family_id=family_id,
        account_id=account_id,
    )


@reports_router.get(
    "/export.csv",
    status_code=status.HTTP_200_OK,
    summary="Xuất báo cáo chi tiết ra file CSV",
    description="Xuất danh sách các giao dịch thu, chi và phí chuyển tiền hợp lệ trong kỳ ra file CSV.",
)
def export_report_csv(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[date, Query(description="Ngày bắt đầu (YYYY-MM-DD)")],
    date_to: Annotated[date, Query(description="Ngày kết thúc (YYYY-MM-DD)")],
    scope: Annotated[
        Literal["all", "personal", "family"],
        Query(description="Phạm vi thống kê: 'all', 'personal' hoặc 'family'"),
    ] = "all",
    family_id: Annotated[
        uuid.UUID | None,
        Query(description="ID nhóm gia đình (tùy chọn)"),
    ] = None,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="ID ví tài khoản cụ thể (tùy chọn)"),
    ] = None,
) -> Response:
    csv_content = ReportService.export_csv(
        db=db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        scope=scope,
        family_id=family_id,
        account_id=account_id,
    )

    filename = f"bao-cao-tai-chinh_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    encoded_filename = urllib.parse.quote(filename)

    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}",
        "Content-Type": "text/csv; charset=utf-8",
    }

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers=headers,
    )

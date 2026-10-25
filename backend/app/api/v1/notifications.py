import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationSyncResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/sync",
    response_model=NotificationSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Đồng bộ thông báo tài chính idempotent",
)
def sync_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationSyncResponse:
    """Quét các nguồn thông báo (khoản định kỳ sắp/quá hạn, ngân sách vượt/chạm ngưỡng) và đồng bộ idempotent."""
    return NotificationService.sync_notifications(db=db, user=current_user)


@router.get(
    "",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách thông báo",
)
def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    include_archived: bool = Query(False, description="Bao gồm thông báo đã lưu trữ"),
    type: str | None = Query(None, description="Lọc theo loại thông báo"),
    limit: int = Query(50, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
) -> list[NotificationResponse]:
    """Lấy danh sách thông báo của người dùng hiện tại có hỗ trợ phân trang và lọc."""
    return NotificationService.get_notifications(
        db=db,
        user=current_user,
        unread_only=unread_only,
        include_archived=include_archived,
        type_=type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Đếm số thông báo chưa đọc",
)
def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationUnreadCountResponse:
    """Trả về số lượng thông báo chưa đọc và chưa lưu trữ của người dùng hiện tại."""
    count = NotificationService.get_unread_count(db=db, user=current_user)
    return NotificationUnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu một thông báo là đã đọc",
)
def mark_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationResponse:
    """Đánh dấu một thông báo là đã đọc."""
    return NotificationService.mark_as_read(db=db, user=current_user, notification_id=notification_id)


@router.post(
    "/mark-all-read",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Đánh dấu tất cả thông báo là đã đọc",
)
def mark_all_as_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    """Đánh dấu toàn bộ thông báo chưa đọc của user hiện tại là đã đọc."""
    updated = NotificationService.mark_all_as_read(db=db, user=current_user)
    return {"marked_count": updated}


@router.post(
    "/{notification_id}/archive",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Lưu trữ thông báo",
)
def archive_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationResponse:
    """Lưu trữ một thông báo để ẩn khỏi danh sách chính mà không xóa lịch sử."""
    return NotificationService.archive_notification(db=db, user=current_user, notification_id=notification_id)

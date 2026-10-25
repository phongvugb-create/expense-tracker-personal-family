import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationType = Literal[
    "recurring_due_soon",
    "recurring_due_today",
    "recurring_overdue",
    "budget_warning",
    "budget_exceeded",
    "system",
]


class NotificationResponse(BaseModel):
    """Schema dữ liệu trả về của một thông báo."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    source_key: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    action_url: str | None = None
    metadata: dict[str, Any] | None = Field(default=None, serialization_alias="metadata")
    read_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificationUnreadCountResponse(BaseModel):
    """Schema số lượng thông báo chưa đọc."""

    unread_count: int


class NotificationSyncResponse(BaseModel):
    """Schema kết quả sau khi đồng bộ thông báo."""

    created_count: int
    updated_count: int
    unread_count: int
    message: str

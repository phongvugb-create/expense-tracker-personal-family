from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.family import (
    FamilyCreateRequest,
    FamilyInvitationAcceptRequest,
    FamilyInvitationCreateRequest,
    FamilyInvitationResponse,
    FamilyMemberResponse,
    FamilyMemberRoleUpdateRequest,
    FamilyResponse,
    FamilyUpdateRequest,
)
from app.services.family_service import FamilyService

router = APIRouter(prefix="/families", tags=["Families"])


# ==============================================================================
# 1. Nhóm gia đình (Families)
# ==============================================================================
@router.get(
    "",
    response_model=list[FamilyResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách nhóm gia đình được phép truy cập",
)
def get_families(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FamilyResponse]:
    """Trả về danh sách nhóm gia đình mà user là chủ sở hữu hoặc thành viên đang hoạt động."""
    return FamilyService.get_user_families(db=db, current_user=current_user)


@router.post(
    "",
    response_model=FamilyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo nhóm gia đình mới",
)
def create_family(
    request: FamilyCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyResponse:
    """Tạo nhóm gia đình mới với chủ sở hữu là người dùng hiện tại."""
    return FamilyService.create_family(
        db=db, current_user=current_user, request=request
    )


# Lưu ý đặt route /invitations/accept TRƯỚC /{family_id} để tránh xung đột path parameter
@router.post(
    "/invitations/accept",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Chấp nhận lời mời tham gia nhóm gia đình bằng token",
)
def accept_invitation(
    request: FamilyInvitationAcceptRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyMemberResponse:
    """Xác thực token lời mời và thêm người dùng vào nhóm gia đình với vai trò được mời."""
    return FamilyService.accept_invitation(
        db=db, current_user=current_user, request=request
    )


@router.get(
    "/{family_id}",
    response_model=FamilyResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem thông tin chi tiết nhóm gia đình",
)
def get_family_detail(
    family_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyResponse:
    """Xem chi tiết thông tin nhóm gia đình nếu có quyền truy cập."""
    return FamilyService.get_family_detail(
        db=db, family_id=family_id, current_user=current_user
    )


@router.patch(
    "/{family_id}",
    response_model=FamilyResponse,
    status_code=status.HTTP_200_OK,
    summary="Chỉnh sửa tên nhóm gia đình",
)
def update_family(
    family_id: UUID,
    request: FamilyUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyResponse:
    """Chỉnh sửa tên nhóm gia đình (chỉ Owner có quyền)."""
    return FamilyService.update_family(
        db=db, family_id=family_id, current_user=current_user, request=request
    )


# ==============================================================================
# 2. Thành viên & Vai trò (Members & Roles)
# ==============================================================================
@router.get(
    "/{family_id}/members",
    response_model=list[FamilyMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách thành viên trong nhóm gia đình",
)
def get_family_members(
    family_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FamilyMemberResponse]:
    """Xem danh sách các thành viên đang hoạt động kèm vai trò tương ứng."""
    return FamilyService.get_family_members(
        db=db, family_id=family_id, current_user=current_user
    )


@router.patch(
    "/{family_id}/members/{member_id}/role",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Thay đổi vai trò thành viên trong nhóm",
)
def update_member_role(
    family_id: UUID,
    member_id: UUID,
    request: FamilyMemberRoleUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyMemberResponse:
    """Thay đổi vai trò (editor/viewer) của thành viên (chỉ Owner có quyền)."""
    return FamilyService.update_member_role(
        db=db,
        family_id=family_id,
        member_id=member_id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/{family_id}/members/{member_id}/leave",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Thành viên rời nhóm hoặc Owner xóa thành viên",
)
def leave_family(
    family_id: UUID,
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Đánh dấu thành viên đã rời nhóm gia đình (soft-leave bằng left_at)."""
    return FamilyService.leave_family(
        db=db, family_id=family_id, member_id=member_id, current_user=current_user
    )


# ==============================================================================
# 3. Lời mời thành viên (Invitations)
# ==============================================================================
@router.post(
    "/{family_id}/invitations",
    response_model=FamilyInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lời mời thành viên tham gia nhóm gia đình",
)
def create_invitation(
    family_id: UUID,
    request: FamilyInvitationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyInvitationResponse:
    """Tạo lời mời qua email với vai trò editor hoặc viewer (Owner hoặc Editor có quyền)."""
    return FamilyService.create_invitation(
        db=db, family_id=family_id, current_user=current_user, request=request
    )


@router.get(
    "/{family_id}/invitations",
    response_model=list[FamilyInvitationResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách lời mời của nhóm gia đình",
)
def get_family_invitations(
    family_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FamilyInvitationResponse]:
    """Xem danh sách lời mời (chỉ Owner hoặc Editor có quyền)."""
    return FamilyService.get_family_invitations(
        db=db, family_id=family_id, current_user=current_user
    )


@router.post(
    "/{family_id}/invitations/{invitation_id}/revoke",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Thu hồi lời mời chưa được chấp nhận",
)
def revoke_invitation(
    family_id: UUID,
    invitation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Thu hồi lời mời đang chờ xử lý (chỉ Owner hoặc Editor có quyền)."""
    return FamilyService.revoke_invitation(
        db=db,
        family_id=family_id,
        invitation_id=invitation_id,
        current_user=current_user,
    )

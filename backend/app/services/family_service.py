import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_session_token, hash_session_token
from app.models.family import Family
from app.models.family_invitation import FamilyInvitation
from app.models.family_member import FamilyMember
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

logger = logging.getLogger(__name__)


class FamilyService:
    """Service xử lý nghiệp vụ nhóm gia đình, thành viên và lời mời."""

    @staticmethod
    def get_user_family_role(
        db: Session, family: Family, user: User
    ) -> str | None:
        """
        Xác định vai trò của user trong nhóm gia đình:
        - 'owner': nếu user.id == family.owner_user_id
        - 'owner', 'editor', 'viewer': lấy từ FamilyMember nếu đang active (left_at IS NULL)
        - None: không có quyền hoặc đã rời nhóm
        """
        if family.owner_user_id == user.id:
            return "owner"

        member = db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == family.id,
                FamilyMember.user_id == user.id,
                FamilyMember.left_at.is_(None),
            )
        )
        if member is not None:
            return member.role
        return None

    @staticmethod
    def _check_permission(
        db: Session, family_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> tuple[Family, str]:
        """
        Kiểm tra và trả về (Family, user_role).
        Bắn HTTPException(404) nếu nhóm không tồn tại hoặc user không có quyền xem;
        Bắn HTTPException(403) nếu user có quyền xem nhưng không đủ quyền cho thao tác (required_role).
        """
        family = db.get(Family, family_id)
        if family is None or family.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nhóm gia đình không tồn tại hoặc đã bị xóa.",
            )

        user_role = FamilyService.get_user_family_role(db, family, user)
        if user_role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nhóm gia đình không tồn tại hoặc bạn không có quyền truy cập.",
            )

        # Kiểm tra thứ bậc quyền: owner > editor > viewer
        role_hierarchy = {"owner": 3, "editor": 2, "viewer": 1}
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 1)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Thao tác này yêu cầu quyền tối thiểu là {required_role}.",
            )

        return family, user_role

    # ==========================================================================
    # 1. Nhóm gia đình (Families CRUD)
    # ==========================================================================
    @staticmethod
    def get_user_families(db: Session, current_user: User) -> list[FamilyResponse]:
        """Lấy danh sách các nhóm gia đình mà user có quyền truy cập."""
        # Lấy tất cả gia đình user làm owner
        owned_families = db.scalars(
            select(Family).where(
                Family.owner_user_id == current_user.id,
                Family.deleted_at.is_(None),
            ).order_by(Family.created_at.desc())
        ).all()

        # Lấy tất cả gia đình user là active member
        member_families = db.scalars(
            select(Family)
            .join(FamilyMember, Family.id == FamilyMember.family_id)
            .where(
                FamilyMember.user_id == current_user.id,
                FamilyMember.left_at.is_(None),
                Family.deleted_at.is_(None),
                Family.owner_user_id != current_user.id,  # Tránh trùng lặp
            )
            .order_by(Family.created_at.desc())
        ).all()

        all_families = list(owned_families) + list(member_families)
        if not all_families:
            return []

        # Đếm số lượng thành viên đang active cho từng gia đình
        family_ids = [f.id for f in all_families]
        counts_query = (
            select(FamilyMember.family_id, func.count(FamilyMember.id))
            .where(
                FamilyMember.family_id.in_(family_ids),
                FamilyMember.left_at.is_(None),
            )
            .group_by(FamilyMember.family_id)
        )
        counts_dict = dict(db.execute(counts_query).all())

        results: list[FamilyResponse] = []
        for fam in all_families:
            role = FamilyService.get_user_family_role(db, fam, current_user)
            # Tổng số thành viên = số active members + 1 (owner nếu owner không có trong FamilyMember)
            # Kiểm tra xem owner có trong FamilyMember không:
            owner_in_members = db.scalar(
                select(func.count(FamilyMember.id)).where(
                    FamilyMember.family_id == fam.id,
                    FamilyMember.user_id == fam.owner_user_id,
                    FamilyMember.left_at.is_(None),
                )
            )
            total_members = counts_dict.get(fam.id, 0)
            if not owner_in_members:
                total_members += 1

            results.append(
                FamilyResponse(
                    id=fam.id,
                    name=fam.name,
                    owner_user_id=fam.owner_user_id,
                    my_role=role or "viewer",  # type: ignore[arg-type]
                    member_count=total_members,
                    created_at=fam.created_at,
                    updated_at=fam.updated_at,
                )
            )

        return results

    @staticmethod
    def create_family(
        db: Session, current_user: User, request: FamilyCreateRequest
    ) -> FamilyResponse:
        """Tạo nhóm gia đình mới với owner là current_user."""
        new_family = Family(
            name=request.name.strip(),
            owner_user_id=current_user.id,
        )
        db.add(new_family)
        db.commit()
        db.refresh(new_family)

        return FamilyResponse(
            id=new_family.id,
            name=new_family.name,
            owner_user_id=new_family.owner_user_id,
            my_role="owner",
            member_count=1,
            created_at=new_family.created_at,
            updated_at=new_family.updated_at,
        )

    @staticmethod
    def get_family_detail(
        db: Session, family_id: uuid.UUID, current_user: User
    ) -> FamilyResponse:
        """Xem chi tiết nhóm gia đình."""
        family, user_role = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="viewer"
        )

        # Tính member_count
        active_count = db.scalar(
            select(func.count(FamilyMember.id)).where(
                FamilyMember.family_id == family.id,
                FamilyMember.left_at.is_(None),
            )
        ) or 0
        owner_in_members = db.scalar(
            select(func.count(FamilyMember.id)).where(
                FamilyMember.family_id == family.id,
                FamilyMember.user_id == family.owner_user_id,
                FamilyMember.left_at.is_(None),
            )
        )
        total_members = active_count + (0 if owner_in_members else 1)

        return FamilyResponse(
            id=family.id,
            name=family.name,
            owner_user_id=family.owner_user_id,
            my_role=user_role,  # type: ignore[arg-type]
            member_count=total_members,
            created_at=family.created_at,
            updated_at=family.updated_at,
        )

    @staticmethod
    def update_family(
        db: Session,
        family_id: uuid.UUID,
        current_user: User,
        request: FamilyUpdateRequest,
    ) -> FamilyResponse:
        """Chỉnh sửa tên nhóm gia đình (chỉ Owner có quyền)."""
        family, _user_role = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="owner"
        )

        family.name = request.name.strip()
        db.commit()
        db.refresh(family)

        return FamilyService.get_family_detail(db, family.id, current_user)

    # ==========================================================================
    # 2. Quản lý thành viên (Members & Roles)
    # ==========================================================================
    @staticmethod
    def get_family_members(
        db: Session, family_id: uuid.UUID, current_user: User
    ) -> list[FamilyMemberResponse]:
        """Lấy danh sách các thành viên đang hoạt động trong nhóm gia đình."""
        family, _ = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="viewer"
        )

        # 1. Truy vấn các active members trong FamilyMember
        members = db.scalars(
            select(FamilyMember)
            .where(
                FamilyMember.family_id == family.id,
                FamilyMember.left_at.is_(None),
            )
            .order_by(FamilyMember.joined_at.asc())
        ).all()

        results: list[FamilyMemberResponse] = []
        owner_included = False

        for m in members:
            u = db.get(User, m.user_id)
            if u is None:
                continue
            is_owner = (m.user_id == family.owner_user_id)
            if is_owner:
                owner_included = True

            results.append(
                FamilyMemberResponse(
                    id=m.id,
                    user_id=u.id,
                    display_name=u.display_name,
                    email=u.email,
                    avatar_url=u.avatar_url,
                    role="owner" if is_owner else m.role,  # type: ignore[arg-type]
                    joined_at=m.joined_at,
                    is_owner=is_owner,
                )
            )

        # 2. Nếu owner chưa có trong danh sách FamilyMember -> bổ sung owner vào đầu danh sách
        if not owner_included:
            owner_user = db.get(User, family.owner_user_id)
            if owner_user is not None:
                results.insert(
                    0,
                    FamilyMemberResponse(
                        id=family.id,  # Dùng family.id đại diện cho member_id của owner khi chưa có row riêng
                        user_id=owner_user.id,
                        display_name=owner_user.display_name,
                        email=owner_user.email,
                        avatar_url=owner_user.avatar_url,
                        role="owner",
                        joined_at=family.created_at,
                        is_owner=True,
                    ),
                )

        return results

    @staticmethod
    def update_member_role(
        db: Session,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        current_user: User,
        request: FamilyMemberRoleUpdateRequest,
    ) -> FamilyMemberResponse:
        """Thay đổi vai trò của thành viên trong nhóm (chỉ Owner có quyền)."""
        family, _ = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="owner"
        )

        member = db.get(FamilyMember, member_id)
        if member is None or member.family_id != family.id or member.left_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thành viên không tồn tại trong nhóm gia đình này.",
            )

        if member.user_id == family.owner_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thay đổi vai trò của chủ sở hữu nhóm gia đình.",
            )

        if request.role not in ("editor", "viewer"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vai trò thành viên chỉ có thể là 'editor' hoặc 'viewer'.",
            )

        member.role = request.role
        db.commit()
        db.refresh(member)

        u = db.get(User, member.user_id)
        return FamilyMemberResponse(
            id=member.id,
            user_id=member.user_id,
            display_name=u.display_name if u else "Unknown",
            email=u.email if u else "",
            avatar_url=u.avatar_url if u else None,
            role=member.role,  # type: ignore[arg-type]
            joined_at=member.joined_at,
            is_owner=False,
        )

    @staticmethod
    def leave_family(
        db: Session, family_id: uuid.UUID, member_id: uuid.UUID, current_user: User
    ) -> dict[str, str]:
        """Thành viên rời khỏi nhóm gia đình, hoặc Owner xóa thành viên khỏi nhóm."""
        family, user_role = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="viewer"
        )

        member = db.get(FamilyMember, member_id)
        if member is None or member.family_id != family.id or member.left_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thành viên không tồn tại hoặc đã rời nhóm gia đình.",
            )

        # Chủ sở hữu không thể tự rời nhóm theo luồng này
        if member.user_id == family.owner_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chủ sở hữu nhóm không thể rời nhóm khi chưa chuyển giao quyền sở hữu.",
            )

        # Chỉ có chính thành viên đó (tự rời) HOẶC Owner nhóm (kick) mới được thao tác
        if member.user_id != current_user.id and user_role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác rời nhóm cho thành viên này.",
            )

        # Cập nhật soft leave bằng left_at
        member.left_at = datetime.now(UTC)
        db.commit()

        return {"message": "Thành viên đã rời nhóm gia đình thành công."}

    # ==========================================================================
    # 3. Lời mời thành viên (Family Invitations)
    # ==========================================================================
    @staticmethod
    def create_invitation(
        db: Session,
        family_id: uuid.UUID,
        current_user: User,
        request: FamilyInvitationCreateRequest,
    ) -> FamilyInvitationResponse:
        """Tạo lời mời tham gia nhóm gia đình (Owner hoặc Editor)."""
        family, _ = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="editor"
        )

        email = request.invited_email.strip().lower()
        if request.role not in ("editor", "viewer"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vai trò được mời chỉ có thể là 'editor' hoặc 'viewer'.",
            )

        # Kiểm tra xem email này đã là thành viên active hay chưa
        existing_user = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing_user is not None:
            if existing_user.id == family.owner_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Người dùng này hiện đã là chủ sở hữu nhóm gia đình.",
                )
            active_member = db.scalar(
                select(FamilyMember).where(
                    FamilyMember.family_id == family.id,
                    FamilyMember.user_id == existing_user.id,
                    FamilyMember.left_at.is_(None),
                )
            )
            if active_member is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Người dùng này hiện đã là thành viên đang hoạt động trong nhóm.",
                )

        # Kiểm tra xem có lời mời nào đang pending cho email này không
        now = datetime.now(UTC)
        pending_invitations = db.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.family_id == family.id,
                FamilyInvitation.invited_email == email,
                FamilyInvitation.accepted_at.is_(None),
                FamilyInvitation.declined_at.is_(None),
                FamilyInvitation.revoked_at.is_(None),
                FamilyInvitation.expires_at > now,
            )
        ).all()

        # Thu hồi các lời mời cũ trước khi tạo lời mời mới để tránh trùng lặp
        for inv in pending_invitations:
            inv.revoked_at = now

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        expires_at = now + timedelta(days=settings.FAMILY_INVITATION_EXPIRE_DAYS)

        new_invitation = FamilyInvitation(
            family_id=family.id,
            inviter_id=current_user.id,
            invited_email=email,
            token_hash=token_hash,
            role=request.role,
            expires_at=expires_at,
        )
        db.add(new_invitation)
        db.commit()
        db.refresh(new_invitation)

        # Token dạng thô chỉ trả về nếu bật setting RETURN_INVITATION_TOKEN_IN_DEV
        invitation_token = raw_token if settings.RETURN_INVITATION_TOKEN_IN_DEV else None

        return FamilyInvitationResponse(
            id=new_invitation.id,
            family_id=new_invitation.family_id,
            inviter_id=new_invitation.inviter_id,
            inviter_name=current_user.display_name,
            invited_email=new_invitation.invited_email,
            role=new_invitation.role,  # type: ignore[arg-type]
            expires_at=new_invitation.expires_at,
            created_at=new_invitation.created_at,
            status="pending",
            invitation_token=invitation_token,
        )

    @staticmethod
    def get_family_invitations(
        db: Session, family_id: uuid.UUID, current_user: User
    ) -> list[FamilyInvitationResponse]:
        """Liệt kê danh sách lời mời của nhóm (chỉ Owner và Editor)."""
        family, _ = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="editor"
        )

        invitations = db.scalars(
            select(FamilyInvitation)
            .where(FamilyInvitation.family_id == family.id)
            .order_by(FamilyInvitation.created_at.desc())
        ).all()

        results: list[FamilyInvitationResponse] = []
        for inv in invitations:
            inviter = db.get(User, inv.inviter_id)
            results.append(
                FamilyInvitationResponse(
                    id=inv.id,
                    family_id=inv.family_id,
                    inviter_id=inv.inviter_id,
                    inviter_name=inviter.display_name if inviter else None,
                    invited_email=inv.invited_email,
                    role=inv.role,  # type: ignore[arg-type]
                    expires_at=inv.expires_at,
                    created_at=inv.created_at,
                    status=inv.status,  # type: ignore[arg-type]
                    invitation_token=None,  # Tuyệt đối không trả token trong danh sách
                )
            )

        return results

    @staticmethod
    def revoke_invitation(
        db: Session,
        family_id: uuid.UUID,
        invitation_id: uuid.UUID,
        current_user: User,
    ) -> dict[str, str]:
        """Thu hồi lời mời chưa được chấp nhận (chỉ Owner và Editor)."""
        family, _ = FamilyService._check_permission(
            db=db, family_id=family_id, user=current_user, required_role="editor"
        )

        invitation = db.get(FamilyInvitation, invitation_id)
        if invitation is None or invitation.family_id != family.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lời mời không tồn tại trong nhóm gia đình này.",
            )

        if not invitation.is_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lời mời không thể thu hồi do đang ở trạng thái '{invitation.status}'.",
            )

        invitation.revoked_at = datetime.now(UTC)
        db.commit()

        return {"message": "Đã thu hồi lời mời thành công."}

    @staticmethod
    def accept_invitation(
        db: Session, current_user: User, request: FamilyInvitationAcceptRequest
    ) -> FamilyMemberResponse:
        """Chấp nhận lời mời tham gia nhóm bằng token bảo mật."""
        raw_token = request.token.strip()
        token_hash = hash_session_token(raw_token)

        # Sử dụng with_for_update để tránh race condition chấp nhận đồng thời
        invitation = db.scalar(
            select(FamilyInvitation)
            .where(FamilyInvitation.token_hash == token_hash)
            .with_for_update()
        )
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mã lời mời không hợp lệ hoặc không tồn tại.",
            )

        if not invitation.is_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lời mời không còn hiệu lực (trạng thái: {invitation.status}).",
            )

        # Xác thực email của user đang đăng nhập khớp với email được mời
        if current_user.email.strip().lower() != invitation.invited_email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email tài khoản đang đăng nhập không trùng khớp với email được mời.",
            )

        family = db.get(Family, invitation.family_id)
        if family is None or family.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nhóm gia đình đã bị xóa hoặc không còn tồn tại.",
            )

        if family.owner_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn đã là chủ sở hữu của nhóm gia đình này.",
            )

        # Kiểm tra xem user đã là thành viên đang active chưa
        existing_member = db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == family.id,
                FamilyMember.user_id == current_user.id,
            )
        )

        now = datetime.now(UTC)
        if existing_member is not None:
            if existing_member.left_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bạn đã là thành viên đang hoạt động trong nhóm gia đình này.",
                )
            # Thành viên cũ quay lại nhóm -> cập nhật lại role và xóa left_at
            existing_member.role = invitation.role
            existing_member.left_at = None
            existing_member.joined_at = now
            member_record = existing_member
        else:
            # Thành viên mới
            member_record = FamilyMember(
                family_id=family.id,
                user_id=current_user.id,
                role=invitation.role,
                joined_at=now,
            )
            db.add(member_record)

        # Cập nhật lời mời thành accepted
        invitation.accepted_at = now
        invitation.accepted_by_user_id = current_user.id

        db.commit()
        db.refresh(member_record)

        return FamilyMemberResponse(
            id=member_record.id,
            user_id=current_user.id,
            display_name=current_user.display_name,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
            role=member_record.role,  # type: ignore[arg-type]
            joined_at=member_record.joined_at,
            is_owner=False,
        )

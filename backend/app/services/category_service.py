import logging
import uuid
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)

logger = logging.getLogger(__name__)


class CategoryService:
    """Service xử lý nghiệp vụ danh mục thu chi, phân quyền và kiểm soát cây danh mục."""

    @staticmethod
    def _get_accessible_family_ids(db: Session, user: User) -> set[uuid.UUID]:
        """Lấy danh sách các family_id mà user có quyền xem (owner hoặc active member)."""
        stmt = (
            select(Family.id)
            .where(
                Family.owner_user_id == user.id,
                Family.deleted_at.is_(None),
            )
            .union(
                select(FamilyMember.family_id)
                .join(Family, FamilyMember.family_id == Family.id)
                .where(
                    FamilyMember.user_id == user.id,
                    FamilyMember.left_at.is_(None),
                    Family.deleted_at.is_(None),
                )
            )
        )
        return set(db.scalars(stmt).all())

    @staticmethod
    def _check_family_role(
        db: Session, family_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> bool:
        """
        Kiểm tra quyền của người dùng đối với nhóm gia đình:
        - required_role='viewer': owner, editor, viewer (active).
        - required_role='editor': owner, editor (active).
        - required_role='owner': owner.
        """
        family = db.get(Family, family_id)
        if family is None or family.deleted_at is not None:
            return False

        if family.owner_user_id == user.id:
            return True

        member = db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user.id,
                FamilyMember.left_at.is_(None),
            )
        )
        if member is None:
            return False

        if required_role == "viewer":
            return member.role in ("owner", "editor", "viewer")
        elif required_role == "editor":
            return member.role in ("owner", "editor")
        elif required_role == "owner":
            return member.role == "owner"

        return False

    @staticmethod
    def _validate_parent_category(
        db: Session,
        parent_id: uuid.UUID,
        child_type: str,
        child_scope: str,
        child_user_id: uuid.UUID | None,
        child_family_id: uuid.UUID | None,
        current_user: User,
        current_category_id: uuid.UUID | None = None,
    ) -> Category:
        """
        Xác thực tính hợp lệ của danh mục cha:
        1. Danh mục cha tồn tại và chưa bị xóa mềm.
        2. Không bị lưu trữ (is_archived = False).
        3. Cùng loại thu chi (child_type == parent.type).
        4. Không tự chọn chính mình làm cha (parent_id != current_category_id).
        5. Không tạo vòng lặp (cycle prevention).
        6. Tính tương thích phạm vi sở hữu (scope compatibility):
           - child_scope='personal': parent phải là system HOẶC personal của chính current_user.
           - child_scope='family': parent phải là system HOẶC family của cùng family_id.
        """
        if current_category_id and parent_id == current_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục không thể làm cha của chính nó.",
            )

        parent = db.get(Category, parent_id)
        if parent is None or parent.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục cha không tồn tại hoặc đã bị xóa.",
            )

        if parent.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể chọn danh mục cha đang bị lưu trữ.",
            )

        if parent.type != child_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Danh mục cha phải cùng loại ({child_type}).",
            )

        # Kiểm tra phạm vi sở hữu tương thích
        if child_scope == "personal":
            if parent.scope == "system":
                pass  # Danh mục cá nhân có thể làm con của danh mục hệ thống
            elif parent.scope == "personal" and parent.user_id == current_user.id:
                pass  # Danh mục cá nhân có thể làm con của danh mục cá nhân của chính mình
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục cá nhân chỉ có thể làm con của danh mục hệ thống hoặc danh mục cá nhân của chính bạn.",
                )
        elif child_scope == "family":
            if parent.scope == "system":
                pass  # Danh mục gia đình có thể làm con của danh mục hệ thống
            elif parent.scope == "family" and parent.family_id == child_family_id:
                pass  # Danh mục gia đình có thể làm con của danh mục thuộc cùng nhóm gia đình
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục gia đình chỉ có thể làm con của danh mục hệ thống hoặc danh mục thuộc cùng nhóm gia đình.",
                )

        # Ngăn ngừa vòng lặp: Duyệt ngược từ parent lên root
        if current_category_id:
            curr = parent
            visited = {current_category_id}
            while curr and curr.parent_id:
                if curr.parent_id in visited:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phát hiện quan hệ vòng lặp trong cây danh mục.",
                    )
                visited.add(curr.parent_id)
                curr = db.get(Category, curr.parent_id)

        return parent

    @staticmethod
    def get_categories(
        db: Session,
        current_user: User,
        type_: Literal["income", "expense"] | None = None,
        scope: Literal["system", "personal", "family"] | None = None,
        family_id: uuid.UUID | None = None,
        include_archived: bool = False,
    ) -> list[CategoryResponse]:
        """
        Truy vấn danh mục mà người dùng có quyền xem:
        - Scope system: hiển thị cho mọi user đăng nhập.
        - Scope personal: chỉ hiển thị cho current_user.
        - Scope family: chỉ hiển thị cho nhóm mà user có quyền (owner hoặc active member).
        """
        accessible_family_ids = CategoryService._get_accessible_family_ids(db, current_user)

        conditions = [Category.deleted_at.is_(None)]

        if not include_archived:
            conditions.append(Category.is_archived.is_(False))

        if type_:
            conditions.append(Category.type == type_)

        # Lọc theo scope
        if scope == "system":
            conditions.append(Category.scope == "system")
        elif scope == "personal":
            conditions.append(Category.scope == "personal")
            conditions.append(Category.user_id == current_user.id)
        elif scope == "family":
            conditions.append(Category.scope == "family")
            if family_id:
                if family_id not in accessible_family_ids:
                    return []
                conditions.append(Category.family_id == family_id)
            else:
                if not accessible_family_ids:
                    return []
                conditions.append(Category.family_id.in_(accessible_family_ids))
        else:
            # Tất cả các scope mà user được phép xem
            scope_conditions = [
                Category.scope == "system",
                (Category.scope == "personal") & (Category.user_id == current_user.id),
            ]
            if accessible_family_ids:
                scope_conditions.append(
                    (Category.scope == "family") & (Category.family_id.in_(accessible_family_ids))
                )
            conditions.append(or_(*scope_conditions))

            if family_id:
                if family_id not in accessible_family_ids:
                    return []
                conditions.append(Category.family_id == family_id)

        categories = db.scalars(
            select(Category).where(*conditions).order_by(Category.name.asc())
        ).all()

        return [
            CategoryResponse(
                id=c.id,
                name=c.name,
                type=c.type,  # type: ignore[arg-type]
                scope=c.scope,  # type: ignore[arg-type]
                user_id=c.user_id,
                family_id=c.family_id,
                parent_id=c.parent_id,
                icon=c.icon,
                color=c.color,
                is_default=c.is_default,
                is_archived=c.is_archived,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in categories
        ]

    @staticmethod
    def create_category(
        db: Session,
        current_user: User,
        request: CategoryCreateRequest,
    ) -> CategoryResponse:
        """Tạo danh mục mới cho cá nhân hoặc nhóm gia đình."""
        name = request.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên danh mục không được để trống.",
            )

        if request.scope == "personal":
            if request.family_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục cá nhân không được gắn family_id.",
                )
            user_id = current_user.id
            family_id = None

        elif request.scope == "family":
            if request.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục gia đình bắt buộc phải cung cấp family_id.",
                )
            # Kiểm tra quyền tạo danh mục gia đình (owner hoặc editor)
            has_permission = CategoryService._check_family_role(
                db=db,
                family_id=request.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền tạo danh mục cho nhóm gia đình này.",
                )
            user_id = None
            family_id = request.family_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phạm vi danh mục không hợp lệ.",
            )

        # Kiểm tra danh mục cha nếu có
        if request.parent_id:
            CategoryService._validate_parent_category(
                db=db,
                parent_id=request.parent_id,
                child_type=request.type,
                child_scope=request.scope,
                child_user_id=user_id,
                child_family_id=family_id,
                current_user=current_user,
            )

        new_category = Category(
            name=name,
            type=request.type,
            scope=request.scope,
            user_id=user_id,
            family_id=family_id,
            parent_id=request.parent_id,
            icon=request.icon.strip() if request.icon else None,
            color=request.color.strip() if request.color else None,
            is_default=False,
            is_archived=False,
        )

        db.add(new_category)
        db.commit()
        db.refresh(new_category)

        return CategoryResponse(
            id=new_category.id,
            name=new_category.name,
            type=new_category.type,  # type: ignore[arg-type]
            scope=new_category.scope,  # type: ignore[arg-type]
            user_id=new_category.user_id,
            family_id=new_category.family_id,
            parent_id=new_category.parent_id,
            icon=new_category.icon,
            color=new_category.color,
            is_default=new_category.is_default,
            is_archived=new_category.is_archived,
            created_at=new_category.created_at,
            updated_at=new_category.updated_at,
        )

    @staticmethod
    def get_category_detail(
        db: Session,
        category_id: uuid.UUID,
        current_user: User,
    ) -> CategoryResponse:
        """Xem chi tiết danh mục thu/chi."""
        category = db.get(Category, category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        # Kiểm tra quyền xem
        if category.scope == "system":
            pass  # Mọi user đăng nhập đều được xem danh mục system
        elif category.scope == "personal":
            if category.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục không tồn tại.",
                )
        elif category.scope == "family" and (
            category.family_id is None
            or not CategoryService._check_family_role(
                db=db,
                family_id=category.family_id,
                user=current_user,
                required_role="viewer",
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        return CategoryResponse(
            id=category.id,
            name=category.name,
            type=category.type,  # type: ignore[arg-type]
            scope=category.scope,  # type: ignore[arg-type]
            user_id=category.user_id,
            family_id=category.family_id,
            parent_id=category.parent_id,
            icon=category.icon,
            color=category.color,
            is_default=category.is_default,
            is_archived=category.is_archived,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    @staticmethod
    def update_category(
        db: Session,
        category_id: uuid.UUID,
        current_user: User,
        request: CategoryUpdateRequest,
    ) -> CategoryResponse:
        """Chỉnh sửa danh mục thu/chi (tên, icon, color)."""
        category = db.get(Category, category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        # Cấm người dùng thông thường sửa danh mục hệ thống
        if category.scope == "system":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không thể chỉnh sửa danh mục hệ thống mặc định.",
            )

        # Kiểm tra quyền sửa
        if category.scope == "personal":
            if category.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục không tồn tại.",
                )
        elif category.scope == "family" and (
            category.family_id is None
            or not CategoryService._check_family_role(
                db=db,
                family_id=category.family_id,
                user=current_user,
                required_role="editor",
            )
        ):
            if category.family_id and CategoryService._check_family_role(
                db=db,
                family_id=category.family_id,
                user=current_user,
                required_role="viewer",
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền chỉnh sửa danh mục của nhóm gia đình này.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        if request.name is not None:
            clean_name = request.name.strip()
            if not clean_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tên danh mục không được để trống.",
                )
            category.name = clean_name

        if request.icon is not None:
            category.icon = request.icon.strip() if request.icon.strip() else None

        if request.color is not None:
            category.color = request.color.strip() if request.color.strip() else None

        db.commit()
        db.refresh(category)

        return CategoryResponse(
            id=category.id,
            name=category.name,
            type=category.type,  # type: ignore[arg-type]
            scope=category.scope,  # type: ignore[arg-type]
            user_id=category.user_id,
            family_id=category.family_id,
            parent_id=category.parent_id,
            icon=category.icon,
            color=category.color,
            is_default=category.is_default,
            is_archived=category.is_archived,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    @staticmethod
    def set_archive_status(
        db: Session,
        category_id: uuid.UUID,
        current_user: User,
        archive: bool,
    ) -> CategoryResponse:
        """Lưu trữ (archive) hoặc khôi phục (restore) danh mục."""
        category = db.get(Category, category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        # Cấm lưu trữ/khôi phục danh mục hệ thống qua API thông thường
        if category.scope == "system":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không thể thay đổi trạng thái lưu trữ của danh mục hệ thống.",
            )

        # Kiểm tra quyền quản lý
        if category.scope == "personal":
            if category.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục không tồn tại.",
                )
        elif category.scope == "family" and (
            category.family_id is None
            or not CategoryService._check_family_role(
                db=db,
                family_id=category.family_id,
                user=current_user,
                required_role="editor",
            )
        ):
            if category.family_id and CategoryService._check_family_role(
                db=db,
                family_id=category.family_id,
                user=current_user,
                required_role="viewer",
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền quản lý lưu trữ danh mục của nhóm gia đình này.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại.",
            )

        # Khi khôi phục một danh mục con, nếu danh mục cha vẫn đang bị lưu trữ -> báo lỗi
        if not archive and category.parent_id:
            parent = db.get(Category, category.parent_id)
            if parent and parent.is_archived:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không thể khôi phục danh mục con khi danh mục cha vẫn đang bị lưu trữ.",
                )

        category.is_archived = archive
        db.commit()
        db.refresh(category)

        return CategoryResponse(
            id=category.id,
            name=category.name,
            type=category.type,  # type: ignore[arg-type]
            scope=category.scope,  # type: ignore[arg-type]
            user_id=category.user_id,
            family_id=category.family_id,
            parent_id=category.parent_id,
            icon=category.icon,
            color=category.color,
            is_default=category.is_default,
            is_archived=category.is_archived,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

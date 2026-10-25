import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transfer import TransferCreateRequest, TransferResponse
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.get(
    "",
    response_model=list[TransferResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem danh sách giao dịch chuyển tiền",
)
def get_transfers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description="Lọc theo ID ví tài chính (ví nguồn hoặc ví đích)"),
    ] = None,
    date_from: Annotated[
        datetime | None,
        Query(description="Thời điểm bắt đầu (occurred_at >= date_from)"),
    ] = None,
    date_to: Annotated[
        datetime | None,
        Query(description="Thời điểm kết thúc (occurred_at <= date_to)"),
    ] = None,
    include_voided: Annotated[
        bool,
        Query(description="Bao gồm cả các giao dịch chuyển tiền đã hủy (void)"),
    ] = False,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Số lượng bản ghi tối đa trả về"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Vị trí bản ghi bắt đầu lấy"),
    ] = 0,
) -> list[TransferResponse]:
    """Lấy danh sách các giao dịch chuyển tiền mà người dùng có quyền truy cập."""
    return TransferService.get_transfers(
        db=db,
        current_user=current_user,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        include_voided=include_voided,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo giao dịch chuyển tiền giữa 2 ví (hạch toán kép)",
)
def create_transfer(
    request: TransferCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransferResponse:
    """
    Thực hiện chuyển tiền giữa 2 ví với bút toán kép nguyên tử (Atomic Unit):
    - Tạo Transfer
    - Tạo Transaction 'transfer_out' tại ví nguồn
    - Tạo Transaction 'transfer_in' tại ví đích
    - Tạo Transaction 'transfer_fee' tại ví nguồn (nếu có phí)
    """
    return TransferService.create_transfer(
        db=db,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết một giao dịch chuyển tiền",
)
def get_transfer_detail(
    transfer_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransferResponse:
    """Trả thông tin chi tiết một lượt chuyển tiền nếu người dùng có quyền xem."""
    return TransferService.get_transfer_detail(
        db=db,
        transfer_id=transfer_id,
        current_user=current_user,
    )


@router.post(
    "/{transfer_id}/void",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy hiệu lực (void) giao dịch chuyển tiền",
)
def void_transfer(
    transfer_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TransferResponse:
    """
    Hủy hiệu lực (void) một giao dịch chuyển tiền:
    - Gán voided_at bằng thời gian hiện tại
    - Giữ nguyên các bản ghi lịch sử Transfer và Transaction
    - Số dư 2 ví tự động hoàn nguyên về trạng thái ban đầu
    """
    return TransferService.void_transfer(
        db=db,
        transfer_id=transfer_id,
        current_user=current_user,
    )

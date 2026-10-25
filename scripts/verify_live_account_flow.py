import sys
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_live_account_flow():
    print("=" * 60)
    print("KIỂM CHỨNG TÍCH HỢP END-TO-END VÍ TÀI KHOẢN VỚI POSTGRESQL THẬT")
    print("=" * 60)

    session = httpx.Client()

    # 1. Đăng ký tài khoản kiểm thử
    test_email = f"test_wallet_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "SecurePassword123!"
    test_name = "Người Dùng Ví Test"

    print(f"1. Đăng ký người dùng: {test_email}")
    reg_res = session.post(
        f"{BASE_URL}/auth/register",
        json={"email": test_email, "password": test_password, "display_name": test_name},
    )
    assert reg_res.status_code == 201, f"Lỗi đăng ký: {reg_res.text}"
    user_data = reg_res.json()
    user_id = user_data["id"]
    print(f"   -> Đăng ký thành công, user_id: {user_id}")

    # 2. Đăng nhập để nhận cookie session
    print("2. Đăng nhập tài khoản...")
    login_res = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert login_res.status_code == 200, f"Lỗi đăng nhập: {login_res.text}"
    assert "session_token" in session.cookies, "Không nhận được cookie session_token"
    print("   -> Đăng nhập thành công, session cookie đã sẵn sàng")

    # 3. Lấy danh sách ví ban đầu (phải rỗng)
    print("3. Kiểm tra danh sách ví ban đầu...")
    get_res = session.get(f"{BASE_URL}/accounts")
    assert get_res.status_code == 200, f"Lỗi lấy ví: {get_res.text}"
    assert len(get_res.json()) == 0, f"Danh sách ban đầu không rỗng: {get_res.json()}"
    print("   -> Danh sách ví ban đầu rỗng chính xác")

    # 4. Tạo ví cá nhân mới
    print("4. Tạo ví cá nhân 'Ví Tiền Mặt Hàng Ngày' (initial_balance: 1.500.000)...")
    create_res = session.post(
        f"{BASE_URL}/accounts",
        json={
            "name": "Ví Tiền Mặt Hàng Ngày",
            "scope": "personal",
            "account_type": "cash",
            "currency": "VND",
            "initial_balance": "1500000.00",
        },
    )
    assert create_res.status_code == 201, f"Lỗi tạo ví: {create_res.text}"
    account = create_res.json()
    account_id = account["id"]
    assert account["name"] == "Ví Tiền Mặt Hàng Ngày"
    assert account["scope"] == "personal"
    assert account["initial_balance"] == "1500000.00"
    assert account["current_balance"] == "1500000.00"
    assert account["is_archived"] is False
    print(f"   -> Tạo ví thành công, account_id: {account_id}")

    # 5. Lấy danh sách ví (phải có 1 ví)
    print("5. Lấy danh sách ví sau khi tạo...")
    list_res = session.get(f"{BASE_URL}/accounts")
    assert list_res.status_code == 200
    acc_list = list_res.json()
    assert len(acc_list) == 1
    assert acc_list[0]["id"] == account_id
    print("   -> Danh sách ví trả về 1 bản ghi chính xác")

    # 6. Cập nhật tên ví
    print("6. Chỉnh sửa tên ví thành 'Ví Tiền Mặt Đã Đổi Tên'...")
    patch_res = session.patch(
        f"{BASE_URL}/accounts/{account_id}",
        json={"name": "Ví Tiền Mặt Đã Đổi Tên"},
    )
    assert patch_res.status_code == 200, f"Lỗi sửa ví: {patch_res.text}"
    assert patch_res.json()["name"] == "Ví Tiền Mặt Đã Đổi Tên"
    print("   -> Cập nhật tên ví thành công")

    # 7. Lưu trữ ví (archive)
    print("7. Lưu trữ ví (POST /archive)...")
    arch_res = session.post(f"{BASE_URL}/accounts/{account_id}/archive")
    assert arch_res.status_code == 200, f"Lỗi lưu trữ ví: {arch_res.text}"
    assert arch_res.json()["is_archived"] is True
    print("   -> Lưu trữ ví thành công")

    # 8. Mặc định GET /accounts không trả ví đã lưu trữ
    print("8. Kiểm tra GET /accounts mặc định không trả ví đã lưu trữ...")
    def_list = session.get(f"{BASE_URL}/accounts").json()
    assert len(def_list) == 0, "Ví lưu trữ vẫn xuất hiện trong danh sách mặc định"
    print("   -> Ví lưu trữ đã được ẩn thành công")

    # 9. GET /accounts?include_archived=true phải thấy ví
    print("9. Kiểm tra GET /accounts?include_archived=true...")
    inc_list = session.get(f"{BASE_URL}/accounts?include_archived=true").json()
    assert len(inc_list) == 1
    assert inc_list[0]["id"] == account_id
    print("   -> Lấy được ví lưu trữ với query include_archived=true thành công")

    # 10. Khôi phục ví (restore)
    print("10. Khôi phục ví (POST /restore)...")
    rest_res = session.post(f"{BASE_URL}/accounts/{account_id}/restore")
    assert rest_res.status_code == 200, f"Lỗi khôi phục ví: {rest_res.text}"
    assert rest_res.json()["is_archived"] is False
    print("   -> Khôi phục ví thành công")

    # 11. Đăng xuất
    print("11. Đăng xuất session...")
    logout_res = session.post(f"{BASE_URL}/auth/logout")
    assert logout_res.status_code == 200
    print("   -> Đăng xuất thành công")

    # 12. Gọi lại khi đã đăng xuất phải nhận 401
    print("12. Gọi lại API sau khi đăng xuất...")
    unauth_res = session.get(f"{BASE_URL}/accounts")
    assert unauth_res.status_code == 401
    print("   -> 401 Unauthorized chính xác!")

    print("=" * 60)
    print("TẤT CẢ 12 BƯỚC XÁC MINH LIVE API & POSTGRESQL ĐỀU THÀNH CÔNG RỰC RỠ!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_live_account_flow()
    except (AssertionError, httpx.HTTPError) as e:
        print(f"XÁC MINH THẤT BẠI: {e}", file=sys.stderr)
        sys.exit(1)

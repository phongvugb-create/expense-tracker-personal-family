import sys
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_live_family_flow():
    print("=" * 60)
    print("KIỂM CHỨNG TÍCH HỢP END-TO-END NHÓM GIA ĐÌNH & LỜI MỜI TRÊN POSTGRESQL THẬT")
    print("=" * 60)

    session_owner = httpx.Client()
    session_guest = httpx.Client()

    suffix = uuid.uuid4().hex[:6]
    owner_email = f"owner_live_{suffix}@example.com"
    guest_email = f"guest_live_{suffix}@example.com"
    password = "SecurePassword123!"

    # 1. Đăng ký & Đăng nhập Owner
    print("1. Đăng ký & Đăng nhập tài khoản Owner...")
    r = session_owner.post(
        f"{BASE_URL}/auth/register",
        json={"email": owner_email, "password": password, "display_name": "Chủ Hộ Live"},
    )
    assert r.status_code == 201, f"Lỗi reg owner: {r.text}"
    r = session_owner.post(f"{BASE_URL}/auth/login", json={"email": owner_email, "password": password})
    assert r.status_code == 200, f"Lỗi login owner: {r.text}"

    # 2. Đăng ký & Đăng nhập Guest
    print("2. Đăng ký & Đăng nhập tài khoản Guest...")
    r = session_guest.post(
        f"{BASE_URL}/auth/register",
        json={"email": guest_email, "password": password, "display_name": "Thành Viên Live"},
    )
    assert r.status_code == 201, f"Lỗi reg guest: {r.text}"
    r = session_guest.post(f"{BASE_URL}/auth/login", json={"email": guest_email, "password": password})
    assert r.status_code == 200, f"Lỗi login guest: {r.text}"

    # 3. Owner tạo nhóm gia đình
    print("3. Owner tạo nhóm gia đình 'Gia Đình Thông Thái'...")
    r = session_owner.post(f"{BASE_URL}/families", json={"name": "Gia Đình Thông Thái"})
    assert r.status_code == 201, f"Lỗi tạo family: {r.text}"
    fam = r.json()
    family_id = fam["id"]
    assert fam["name"] == "Gia Đình Thông Thái"
    assert fam["my_role"] == "owner"
    assert fam["member_count"] == 1
    print(f"   -> Tạo nhóm thành công, family_id: {family_id}")

    # 4. Owner đổi tên nhóm
    print("4. Owner cập nhật tên nhóm...")
    r = session_owner.patch(f"{BASE_URL}/families/{family_id}", json={"name": "Gia Đình Hạnh Phúc Live"})
    assert r.status_code == 200
    assert r.json()["name"] == "Gia Đình Hạnh Phúc Live"
    print("   -> Cập nhật tên nhóm thành công")

    # 5. Owner mời Guest tham gia với vai trò editor
    print(f"5. Owner gửi lời mời cho {guest_email} (role: editor)...")
    r = session_owner.post(
        f"{BASE_URL}/families/{family_id}/invitations",
        json={"invited_email": guest_email, "role": "editor"},
    )
    assert r.status_code == 201, f"Lỗi mời: {r.text}"
    inv_data = r.json()
    token = inv_data["invitation_token"]
    assert token is not None, "Không nhận được invitation_token trong dev/demo mode"
    print("   -> Lời mời đã tạo thành công, nhận token bảo mật")

    # 6. Guest chấp nhận lời mời bằng token
    print("6. Guest chấp nhận lời mời...")
    r = session_guest.post(f"{BASE_URL}/families/invitations/accept", json={"token": token})
    assert r.status_code == 200, f"Lỗi accept: {r.text}"
    member_record = r.json()
    member_id = member_record["id"]
    assert member_record["role"] == "editor"
    print(f"   -> Guest gia nhập nhóm thành công, member_id: {member_id}")

    # 7. Guest xem danh sách nhóm
    print("7. Guest kiểm tra danh sách nhóm gia đình...")
    r = session_guest.get(f"{BASE_URL}/families")
    assert r.status_code == 200
    guest_fams = r.json()
    assert len(guest_fams) == 1
    assert guest_fams[0]["id"] == family_id
    assert guest_fams[0]["my_role"] == "editor"
    assert guest_fams[0]["member_count"] == 2
    print("   -> Guest thấy nhóm với my_role = editor và member_count = 2 chính xác")

    # 8. Xem danh sách thành viên
    print("8. Kiểm tra danh sách thành viên...")
    r = session_owner.get(f"{BASE_URL}/families/{family_id}/members")
    assert r.status_code == 200
    members = r.json()
    assert len(members) == 2
    roles = {m["role"] for m in members}
    assert roles == {"owner", "editor"}
    print("   -> Danh sách thành viên hiển thị đầy đủ Owner và Editor chính xác")

    # 9. Owner thay đổi role của Guest thành viewer
    print("9. Owner hạ quyền Guest xuống viewer...")
    r = session_owner.patch(
        f"{BASE_URL}/families/{family_id}/members/{member_id}/role",
        json={"role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"
    print("   -> Cập nhật vai trò thành công")

    # 10. Guest tự rời nhóm (leave)
    print("10. Guest tự rời nhóm gia đình...")
    r = session_guest.post(f"{BASE_URL}/families/{family_id}/members/{member_id}/leave")
    assert r.status_code == 200
    print("   -> Guest đã rời nhóm thành công")

    # 11. Guest kiểm tra lại danh sách nhóm (phải rỗng)
    print("11. Guest kiểm tra danh sách sau khi rời nhóm...")
    r = session_guest.get(f"{BASE_URL}/families")
    assert r.status_code == 200
    assert len(r.json()) == 0
    print("   -> Nhóm đã được ẩn khỏi Guest chính xác")

    print("=" * 60)
    print("TOÀN BỘ 11 BƯỚC XÁC MINH LIVE FAMILY & INVITATIONS ĐỀU THÀNH CÔNG RỰC RỠ!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_live_family_flow()
    except (AssertionError, httpx.HTTPError) as e:
        print(f"XÁC MINH THẤT BẠI: {e}", file=sys.stderr)
        sys.exit(1)

# KỊCH BẢN TRÌNH DIỄN & BẢO VỆ ĐỒ ÁN (8–12 PHÚT)
# HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN VÀ GIA ĐÌNH

---

## 1. Thông tin Chung & Chuẩn bị Môi trường

- **Thời lượng dự kiến**: 10 phút trình bày + 5 phút trả lời câu hỏi của Hội đồng.
- **Tài khoản Demo chuẩn**:
  - **Email**: `demo@expensetracker-demo.com`
  - **Mật khẩu**: `DemoPassword123@`
- **Địa chỉ truy cập**: `http://localhost:5173` (Frontend) | `http://localhost:8001/api/v1` (Backend).
- **Lệnh phục hồi dữ liệu ban đầu (nếu cần reset trước buổi bảo vệ)**:
  ```powershell
  & "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py
  ```

---

## 2. Kịch bản Chi tiết từng Bước

### PHẦN 1: MỞ ĐẦU & TỔNG QUAN KIẾN TRÚC (1.5 phút)
- **Lời thoại mở đầu**:
  > *"Kính thưa Hội đồng, em xin phép trình bày đồ án tốt nghiệp: 'Hệ thống Quản lý Chi tiêu Cá nhân và Gia đình'. Mục tiêu trọng tâm của đề tài là giải quyết bài toán tách bạch tài chính cá nhân với ngân quỹ sinh hoạt chung gia đình, đảm bảo tính toàn vẹn số dư theo nguyên tắc kế toán kép và bảo mật phiên bằng HttpOnly Cookie."*
- **Tóm tắt kiến trúc**:
  > *"Hệ thống được xây dựng theo kiến trúc 3 lớp: Frontend SPA bằng React 19 + TypeScript với phong cách thiết kế Fresh Family Finance; Backend RESTful API bằng FastAPI và Pydantic v2; Cơ sở dữ liệu lưu trữ 100% dữ liệu thực trên PostgreSQL 18 qua SQLAlchemy 2.0 và quản lý migration bằng Alembic."*

---

### PHẦN 2: XÁC THỰC VÀ BẢO MẬT PHIÊN (1 phút)
- **Route**: `/login`
- **Thao tác thực tế**:
  1. Mở trang đăng nhập tại `http://localhost:5173/login`.
  2. Nhập thông tin tài khoản demo: `demo@expensetracker-demo.com` / `DemoPassword123@`.
  3. Bấm **Đăng Nhập**.
- **Nội dung giải thích**:
  - Hệ thống sử dụng cơ chế **Opaque Stateful Session**: Server sinh token ngẫu nhiên 32-byte an toàn, lưu mã băm SHA-256 trong database và trả token qua **Cookie HttpOnly, SameSite=Lax**.
  - Mật khẩu được băm bằng thuật toán **Argon2id**, ngăn chặn tấn công GPU brute-force và timing attack.
  - Khác với JWT stateless, cơ chế này cho phép thu hồi phiên tức thời (Instant Revocation) khi đăng xuất.
- **Kết quả dự kiến**: Đăng nhập thành công, tự động chuyển hướng vào màn hình Dashboard.

---

### PHẦN 3: TỔNG QUAN DASHBOARD TÀI CHÍNH (1.5 phút)
- **Route**: `/dashboard`
- **Thao tác thực tế**:
  1. Chỉ vào thanh Header 3 vùng: Logo bên trái, 7 nút điều hướng ở giữa, cụm chuông thông báo + hồ sơ người dùng + nút Đăng xuất ở bên phải.
  2. Chỉ vào 4 thẻ chỉ số: **Số Dư Khả Dụng**, **Tổng Thu Trong Kỳ**, **Tổng Chi Trong Kỳ**, **Dòng Tiền Thuần**.
  3. Rê chuột vào từng cột của **Biểu đồ xu hướng 6 tháng**: Tooltip nổi hiển thị chi tiết Thu, Chi, Dòng tiền của tháng được chọn.
  4. Thay đổi bộ lọc Tháng/Năm hoặc Phạm vi (Tất cả / Cá nhân / Gia đình) trên thanh lọc.
- **Nội dung giải thích**:
  - Dashboard tổng hợp trực tiếp từ PostgreSQL theo thời gian thực (real-time aggregation).
  - Thu nhập hiển thị màu xanh lục (`#21845A`), chi tiêu hiển thị màu cam đất (`#C75D49`).
  - Biểu đồ xu hướng tự động cân bằng tỷ lệ để ngay cả những tháng có doanh số nhỏ vẫn hiển thị rõ ràng và có thể tương tác tra cứu số tiền thực tế.
- **Kết quả dự kiến**: Dữ liệu tài chính cập nhật tức thì theo bộ lọc được chọn.

---

### PHẦN 4: QUẢN LÝ VÍ & PHÂN ĐỊNH PHẠM VI (1 phút)
- **Route**: `/accounts`
- **Thao tác thực tế**:
  1. Bấm nút **Quản lý ví** trên header hoặc thẻ shortcut trên Dashboard.
  2. Xem danh sách ví: Ví Tiền mặt (Cá nhân), Tài khoản Ngân hàng (Cá nhân), Quỹ Sinh Hoạt Chung (Gia đình).
  3. Bấm **Tạo ví mới**: Tạo một ví tiền mặt cá nhân mới với số dư ban đầu ví dụ `2.000.000 ₫`.
- **Nội dung giải thích**:
  - Hỗ trợ phân loại loại ví: Tiền mặt, Ngân hàng, Ví điện tử.
  - Phân định rõ phạm vi: Ví cá nhân chỉ chủ sở hữu được thấy; ví gia đình được chia sẻ an toàn cho các thành viên trong nhóm theo phân quyền.
- **Kết quả dự kiến**: Ví mới xuất hiện trong danh sách và số dư khả dụng tổng được cộng dồn chính xác.

---

### PHẦN 5: GHI CHÉP GIAO DỊCH THU CHI (1.5 phút)
- **Route**: `/transactions`
- **Thao tác thực tế**:
  1. Bấm **Sổ giao dịch** trên header.
  2. Bấm nút **Thêm giao dịch**:
     - Chọn Loại: **Chi tiêu** (Expense).
     - Chọn Ví: Ví vừa tạo hoặc Ví tiền mặt.
     - Chọn Danh mục: Ăn uống (Food).
     - Nhập Số tiền: `150.000 ₫`.
     - Nhập Ghi chú: "Ăn trưa tiếp đối tác".
     - Bấm **Lưu giao dịch**.
  3. Mở lại `/accounts` để chỉ cho Hội đồng thấy số dư ví đã tự động trừ đi `150.000 ₫`.
- **Nội dung giải thích**:
  - Giao dịch được xử lý trong database transaction, tự động cập nhật số dư ví đồng thời.
  - Danh mục hỗ trợ phân cấp cha - con.
  - Tính năng xóa mềm (Soft-delete): Không xóa vật lý để bảo toàn lịch sử sổ sách.
- **Kết quả dự kiến**: Giao dịch mới xuất hiện ở đầu bảng, số dư ví giảm ngay lập tức.

---

### PHẦN 6: CHUYỂN TIỀN & BÚT TOÁN KÉP (1.5 phút)
- **Route**: `/transfers`
- **Thao tác thực tế**:
  1. Bấm **Chuyển tiền** trên header.
  2. Bấm **Tạo lệnh chuyển tiền**:
     - Ví nguồn: Tài khoản Ngân hàng.
     - Ví đích: Ví Tiền mặt cá nhân.
     - Số tiền: `500.000 ₫`.
     - Phí giao dịch: `5.000 ₫` (chọn Danh mục phí: Chi phí dịch vụ).
     - Bấm **Thực hiện chuyển tiền**.
  3. Xem chi tiết lệnh chuyển: Hệ thống hiển thị rõ ràng bút toán xuất quỹ, nhập quỹ và khoản trừ phí chuyển.
- **Nội dung giải thích**:
  - Áp dụng nguyên tắc **kế toán kép (Double-entry)**: Chuyển tiền không phải là chi tiêu hay thu nhập, nó chỉ dịch chuyển tài sản giữa hai ví. Do đó, chuyển khoản không làm sai lệch báo cáo thu chi hàng tháng.
  - Thao tác thực hiện nguyên tử: Nếu một trong hai ví cập nhật thất bại, toàn bộ giao dịch được rollback.
  - Hỗ trợ chức năng **Hủy lệnh chuyển (Void transfer)**: Khi hủy, hệ thống tự động đảo ngược bút toán, hoàn trả tiền về ví nguồn nguyên vẹn.
- **Kết quả dự kiến**: Ví nguồn giảm 505.000 ₫, ví đích tăng 500.000 ₫, danh sách chuyển tiền lưu lại bản ghi đầy đủ.

---

### PHẦN 7: NGÂN SÁCH & CẢNH BÁO CHI TIÊU (1 phút)
- **Route**: `/budgets`
- **Thao tác thực tế**:
  1. Bấm **Ngân sách** trên header.
  2. Quan sát các thanh tiến độ ngân sách tháng hiện tại:
     - Danh mục Ăn uống: Hiển thị hạn mức, số tiền đã chi, số tiền còn lại và thanh % tiến độ.
     - Chỉ rõ các trạng thái: An toàn (Xanh), Cảnh báo ngưỡng 80% (Vàng hổ phách), Vượt hạn mức (Đỏ).
- **Nội dung giải thích**:
  - Ngân sách tự động tính tổng số tiền từ các giao dịch chi tiêu thực tế trong tháng tương ứng.
  - Khi tỷ lệ vượt ngưỡng cảnh báo (mặc định 80%), hệ thống tự động sinh cảnh báo và hiển thị banner nhắc nhở ngay trên Dashboard.
- **Kết quả dự kiến**: Thể hiện trực quan khả năng kiểm soát hạn mức chi tiêu.

---

### PHẦN 8: GIAO DỊCH ĐỊNH KỲ & CHỐNG TẠO TRÙNG (1.5 phút)
- **Route**: `/recurring-transactions`
- **Thao tác thực tế**:
  1. Bấm **Định kỳ** trên header.
  2. Xem card **Khoản đến hạn cần xác nhận** (ví dụ: Tiền Internet hoặc Tiền điện).
  3. Bấm **Tạo giao dịch ngay** trên card đến hạn.
  4. Bấm xác nhận: Giao dịch được tạo thành công, ngày đến hạn tự động nhảy sang chu kỳ tháng sau.
  5. Thử bấm lại lần nữa hoặc chỉ vào cơ chế chống trùng: Hệ thống ngăn chặn việc phát sinh trùng lặp khoản chi cho cùng một kỳ hạn.
- **Nội dung giải thích**:
  - Hỗ trợ các chu kỳ lặp: Hàng ngày, Hàng tuần, Hàng tháng, Hàng năm.
  - Cơ chế **Idempotent Transaction**: Bảng `transactions` liên kết khóa ngoại với quy tắc định kỳ và kiểm tra kỳ hạn trong transaction có khóa dòng (`FOR UPDATE`), ngăn chặn trừ tiền 2 lần khi người dùng thao tác nhanh.
- **Kết quả dự kiến**: Khoản chi được ghi vào sổ giao dịch, số dư ví cập nhật, chuông thông báo phát sinh tin mới.

---

### PHẦN 9: TRUNG TÂM THÔNG BÁO & KHÔNG GIAN GIA ĐÌNH (1 phút)
- **Thao tác thực tế**:
  1. Bấm vào **Biểu tượng Chuông** trên Header: Popup nền trắng nổi bật mở ra, hiển thị các thông báo về giao dịch định kỳ vừa tạo và cảnh báo ngân sách.
  2. Bấm **Xem tất cả thông báo**: Chuyển đến `/notifications`, thử lọc tab "Chưa đọc" / "Đã đọc", bấm "Đánh dấu tất cả đã đọc".
  3. Mở `/families`: Xem danh sách thành viên gia đình, phân quyền Chủ gia đình (Owner) và thành viên (Editor/Viewer).
- **Nội dung giải thích**:
  - Chuông thông báo đồng bộ số lượng tin chưa đọc theo thời gian thực qua EventBus `notification-sync`.
  - Phân quyền gia đình rõ ràng: Viewer chỉ có quyền xem, không được thêm/sửa giao dịch của gia đình.
- **Kết quả dự kiến**: Thể hiện tính hoàn thiện và trải nghiệm thân thiện của ứng dụng.

---

### PHẦN 10: TỔNG KẾT & KẾT THÚC (0.5 phút)
- **Lời kết**:
  > *"Kính thưa Hội đồng, toàn bộ 10 chức năng cốt lõi của đồ án đều đã được triển khai hoàn chỉnh, chạy thực tế trên cơ sở dữ liệu PostgreSQL 18 và vượt qua 167 bài kiểm thử tự động. Em xin chân thành cảm ơn các Thầy Cô trong Hội đồng đã lắng nghe và em rất mong nhận được những câu hỏi đóng góp quý báu!"*

---

## 3. Phương án Xử lý Tình huống Bất thường (Fallback Guide)

| Tình huống phát sinh | Nguyên nhân khả dĩ | Thao tác xử lý nhanh |
|---|---|---|
| Dữ liệu demo bị xáo trộn do thao tác thử trước đó | Đã thêm/xóa nhiều giao dịch thử | Mở terminal chạy: `& "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py` (Mất ~3 giây để khôi phục trạng thái chuẩn) |
| Backend báo lỗi không kết nối được DB | Container PostgreSQL bị tạm dừng | Chạy `docker start expense_tracker_db`, kiểm tra lại bằng `scripts/check_demo.ps1` |
| Quên mật khẩu tài khoản demo | Nhập sai ký tự | Tài khoản demo chuẩn: `demo@expensetracker-demo.com` / `DemoPassword123@` |
| Trình duyệt bị zoom quá lớn | Phím tắt Ctrl + cuộn chuột | Nhấn `Ctrl + 0` trên bàn phím để đưa tỷ lệ hiển thị về 100% chuẩn |

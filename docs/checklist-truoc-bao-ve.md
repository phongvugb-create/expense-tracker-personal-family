# Checklist Chuẩn Bị Trước Ngày Bảo Vệ Đồ Án

**Dự án:** Ứng dụng Quản lý Chi tiêu Cá nhân và Gia đình (Expense Tracker)  
**Mục đích:** Danh mục các bước kiểm tra kỹ thuật, kiểm thử môi trường, dữ liệu và quy trình dự phòng nhằm đảm bảo buổi thuyết trình / bảo vệ đồ án diễn ra thuận lợi 100%.

---

## 1. Môi Trường & Hạ Tầng Cơ Sở Dữ Liệu

- [ ] **Docker Engine / Docker Desktop:**
  - [ ] Khởi động Docker Desktop trước buổi bảo vệ ít nhất 30 phút.
  - [ ] Kiểm tra trạng thái Docker daemon: `docker info` không báo lỗi.
- [ ] **Container PostgreSQL 18:**
  - [ ] Kiểm tra container database đang chạy:
    ```powershell
    docker ps --filter "name=expense_tracker_db"
    ```
  - [ ] Xác nhận cổng host: **5434** (được map vào 5432 bên trong container).
  - [ ] Kiểm tra tính sẵn sàng (Healthcheck):
    ```powershell
    docker inspect --format='{{json .State.Health.Status}}' expense_tracker_db
    ```
    *(Kết quả mong muốn: `"healthy"`)*.
- [ ] **Alembic Database Migration:**
  - [ ] Kích hoạt môi trường ảo Python và kiểm tra phiên bản migration hiện tại:
    ```powershell
    & "backend\.venv\Scripts\python.exe" -m alembic -c backend/alembic.ini current
    ```
    *(Phải hiển thị: `4dc2493f258e (head)`)*.
  - [ ] Kiểm tra không còn schema chênh lệch:
    ```powershell
    & "backend\.venv\Scripts\python.exe" -m alembic -c backend/alembic.ini check
    ```
    *(Phải báo: `No new upgrade operations detected`)*.

---

## 2. Khởi Chạy & Kiểm Tra Dịch Vụ Ứng Dụng

- [ ] **Backend FastAPI (Cổng 8001):**
  - [ ] Khởi chạy backend bằng script chuẩn hóa hoặc lệnh trực tiếp:
    ```powershell
    & "backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
    ```
  - [ ] Kiểm tra endpoint Health Liveness:
    ```powershell
    curl http://127.0.0.1:8001/api/v1/health/liveness
    ```
    *(Kết quả: HTTP 200 `{"status": "ok"}`)*.
  - [ ] Kiểm tra endpoint Health Readiness (kết nối PostgreSQL):
    ```powershell
    curl http://127.0.0.1:8001/api/v1/health/readiness
    ```
    *(Kết quả: HTTP 200 `{"status": "ok", "database": "connected"}`)*.
- [ ] **Frontend React + Vite (Cổng 5173):**
  - [ ] Khởi chạy frontend dev server:
    ```powershell
    cd frontend
    npm run dev
    ```
  - [ ] Mở trình duyệt kiểm tra: `http://localhost:5173`.
  - [ ] Kiểm tra không có lỗi biên dịch TypeScript: `npm run build` thành công.
  - [ ] Kiểm tra lint cảnh báo: `npm run lint` không có lỗi nghiêm trọng (0 errors).

---

## 3. Dữ Liệu Demo Chuẩn Bị Trước

- [ ] **Chạy Script Tạo Dữ Liệu Mẫu (Seed Data):**
  - [ ] Chạy lệnh nạp dữ liệu mẫu:
    ```powershell
    & "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py
    ```
  - [ ] Kiểm tra thông tin tài khoản demo chính:
    - **Email:** `demo@expensetracker-demo.com`
    - **Mật khẩu:** `DemoPassword123@`
    - **Tên hiển thị:** `Nguyễn Văn Demo`
- [ ] **Xác nhận số lượng và trạng thái dữ liệu đã nạp:**
  - [ ] Có ít nhất **2 ví cá nhân** (Ví Tiền mặt VND, Ví Ngân hàng VND).
  - [ ] Có ít nhất **1 ví gia đình** thuộc không gian gia đình mẫu ("Gia đình hạnh phúc").
  - [ ] Đầy đủ các danh mục cha - con thiết yếu (Ăn uống, Đi lại, Nhà cửa, Lương...).
  - [ ] Có lịch sử giao dịch thu/chi đa dạng ngày tháng trong tháng hiện tại.
  - [ ] Đã có ít nhất 1 quy tắc giao dịch định kỳ (ví dụ: "Tiền thuê nhà" hoặc "Internet cáp quang").
  - [ ] Ngân sách tháng hiện tại đã được thiết lập (ngân sách chi tiêu đã đạt khoảng 60% - 85% để minh họa thanh tiến trình màu vàng/cam).
  - [ ] Có sẵn 2–3 thông báo chưa đọc trong trung tâm thông báo để chuông hiển thị badge màu đỏ nổi bật.

---

## 4. Kiểm Tra Thao Tác Nghiệp Vụ Trên Trình Duyệt

- [ ] **Đăng nhập & Quản lý Session:**
  - [ ] Đăng nhập thành công với `demo@expensetracker-demo.com`.
  - [ ] Mở DevTools (F12) -> tab **Application / Storage** -> **Cookies**:
    - Xác nhận cookie `session_id` có cờ **HttpOnly: true**, **SameSite: Lax**.
  - [ ] Tải lại trang (F5) -> Vẫn giữ trạng thái đăng nhập mượt mà (không bị đá về `/login`).
- [ ] **Dashboard Tổng quan:**
  - [ ] Thẻ tổng quan hiển thị đúng số dư khả dụng, tổng thu, tổng chi tháng hiện tại.
  - [ ] Biểu đồ cơ cấu chi tiêu (Donut chart) và xu hướng tài chính hiển thị rõ ràng.
  - [ ] Thanh Header hiển thị cân đối trên desktop: Logo bên trái, Điều hướng ở giữa, Chuông thông báo + User profile + Nút Đăng xuất ở bên phải.
- [ ] **Quản lý Ví (Accounts):**
  - [ ] Xem danh sách ví cá nhân và ví gia đình phân nhóm rõ ràng.
  - [ ] Thử thao tác thêm ví mới: Số dư ban đầu tự động sinh transaction "Số dư ban đầu".
- [ ] **Giao dịch Thu / Chi (Transactions):**
  - [ ] Tạo giao dịch chi tiêu mới: Số dư ví nguồn lập tức giảm tương ứng.
  - [ ] Thử sửa giao dịch và xóa mềm (soft-delete): Kiểm tra số dư hoàn nguyên chính xác.
- [ ] **Chuyển tiền giữa các ví (Transfers):**
  - [ ] Thực hiện chuyển tiền giữa 2 ví cá nhân (có phí chuyển hoặc không phí).
  - [ ] Xác nhận giao dịch xuất hiện dưới dạng cặp bút toán liên kết (`transfer_id`), số dư 2 ví tăng/giảm đồng thời.
- [ ] **Ngân sách (Budgets):**
  - [ ] Mở màn hình `/budgets`, kiểm tra thanh tiến trình chi tiêu theo từng danh mục.
- [ ] **Báo cáo & Xuất CSV (Reports):**
  - [ ] Lọc báo cáo theo tháng.
  - [ ] Nhấn nút **Xuất CSV**: Tải file về máy tính, mở thử bằng Microsoft Excel trên Windows.
  - [ ] Xác nhận tiếng Việt có dấu hiển thị chuẩn xác (nhờ tiền tố UTF-8 BOM `\ufeff`).
- [ ] **Giao dịch định kỳ & Thông báo:**
  - [ ] Mở trang `/recurring-transactions`: Quy tắc đang kích hoạt hiển thị rõ ngày chạy tiếp theo.
  - [ ] Nhấp vào biểu tượng Chuông thông báo: Danh sách thông báo mở trơn tru, có thể đánh dấu đã đọc hoặc điều hướng chi tiết.
- [ ] **Không gian gia đình (Families):**
  - [ ] Mở trang `/family`: Xem danh sách thành viên và vai trò (Owner / Editor / Viewer).

---

## 5. Sao Lưu An Toàn & Chuẩn Bị Thiết Bị

- [ ] **Backup mã nguồn & Cơ sở dữ liệu:**
  - [ ] Nén một bản sao lưu toàn bộ thư mục dự án (trừ `node_modules` và `.venv`) sang ổ cứng gắn ngoài hoặc USB cá nhân.
  - [ ] Xuất bản sao lưu database PostgreSQL mẫu:
    ```powershell
    docker exec -t expense_tracker_db pg_dump -U postgres -d expense_tracker > backup_demo_db.sql
    ```
- [ ] **Cấu hình thiết bị trình chiếu:**
  - [ ] Kiểm tra cáp HDMI / Type-C kết nối máy chiếu hoặc màn hình phụ tại phòng hội đồng.
  - [ ] Thử chuyển đổi độ phân giải màn hình về 1920x1080 và 1366x768 để đảm bảo giao diện web tự co giãn responsive tốt, không tràn lề.
  - [ ] Tắt các ứng dụng nhắn tin cá nhân (Zalo, Telegram, Facebook Messenger, Skype...) và thông báo Windows (bật chế độ *Focus Assist / Do Not Disturb*).
  - [ ] Tắt chế độ Sleep / Screen Saver của máy tính khi không cắm sạc.

---

## 6. Kế Hoạch Dự Phòng (Fallback Plan) Khi Có Sự Cố

| Tình huống sự cố | Triệu chứng | Phương án khắc phục tức thì |
|---|---|---|
| **Mất kết nối Internet** | Trình duyệt không tải được trang nếu dùng CDN hoặc tài nguyên online | Dự án được thiết kế chạy **100% Offline trên Localhost**. Mọi CSS, font chữ, icon và thư viện JS đã được đóng gói local trong `node_modules`. Giải thích cho hội đồng rằng hệ thống độc lập hoàn toàn với Internet bên ngoài. |
| **Xung đột cổng 8001 hoặc 5173** | Terminal báo `Address already in use` | Dùng PowerShell kiểm tra tiến trình đang chiếm dụng cổng: `Get-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess` và tắt tiến trình cũ, hoặc khởi động lại terminal. |
| **Database container bị dừng đột ngột** | Backend báo lỗi `500 Internal Server Error` hoặc mất kết nối DB | Mở Docker Desktop kiểm tra hoặc chạy: `docker restart expense_tracker_db`. Chờ 5 giây cho container chuyển sang trạng thái `"healthy"`. |
| **Dữ liệu demo bị rối do thao tác thử** | Số dư âm hoặc giao dịch lung tung trước giờ lên thuyết trình | Chạy lại lệnh seed data: `& "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py` để làm mới toàn bộ dữ liệu về trạng thái mẫu lý tưởng trong 3 giây. |
| **Quên mật khẩu tài khoản demo** | Báo lỗi thông tin đăng nhập không hợp lệ | Đăng nhập đúng thông tin chuẩn đã cố định: `demo@expensetracker-demo.com` / `DemoPassword123@`. |

---

## 7. Những Nội Dung Cần Tự Xác Nhận Trước Buổi Bảo Vệ

- [ ] Họ tên, mã số sinh viên của các thành viên trong nhóm trình bày.
- [ ] Họ tên và học hàm, học vị của Giảng viên hướng dẫn.
- [ ] Thời gian tối đa được phân bổ cho phần thuyết trình (thường từ 10 đến 15 phút) để căn chỉnh tốc độ nói theo `docs/kich-ban-bao-ve-do-an.md`.
- [ ] Phân công người thao tác máy tính (lái demo) và người thuyết trình chính để phối hợp nhịp nhàng.

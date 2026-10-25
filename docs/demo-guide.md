# HƯỚNG DẪN TRÌNH DIỄN ĐỒ ÁN (DEMO GUIDE)
## HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN & GIA ĐÌNH

---

## A. Giới Thiệu Hệ Thống

Dự án **Hệ Thống Quản Lý Chi Tiêu Cá Nhân & Gia Đình** là ứng dụng web toàn diện giúp người dùng giải quyết bài toán quản lý tài chính thực tế:
- **Tách bạch và kết nối linh hoạt**: Quản lý song song tài chính cá nhân độc lập và không gian tài chính chung của gia đình.
- **Tính toán tài chính chuẩn mực**: Áp dụng nguyên tắc bút toán kép (Double-Entry Bookkeeping) cho chuyển tiền giữa các ví, đảm bảo số dư luôn chính xác tuyệt đối mà không gây sai lệch báo cáo thu/chi.
- **Dữ liệu thực tế 100%**: Hoàn toàn không sử dụng dữ liệu tĩnh hay mock-up; toàn bộ nghiệp vụ chạy trực tiếp trên cơ sở dữ liệu PostgreSQL 18.
- **Bảo vệ phiên đăng nhập an toàn**: Xác thực bằng Opaque Session Token có thời hạn, lưu hash SHA-256 trong database và truyền tải an toàn qua cookie HttpOnly.

---

## B. Công Nghệ Thực Tế Được Sử Dụng

- **Giao diện người dùng (Frontend)**: React 18, TypeScript (Strict Mode), Vite, Tailwind/Modern CSS, Recharts, Lucide Icons.
- **Dịch vụ máy chủ (Backend)**: Python 3.14 / 3.12, FastAPI, SQLAlchemy 2.0 (ORM đồng bộ & bất đồng bộ), Pydantic v2.
- **Cơ sở dữ liệu & Di chuyển**: PostgreSQL 18 (Containerized), Alembic Migration (Revision hiện tại: `4dc2493f258e`).
- **Hạ tầng Container**: Docker & Docker Compose.
- **Bảo mật**: Argon2id cho băm mật khẩu, Opaque 256-bit Session Token, Cookie HttpOnly (SameSite=Lax).

---

## C. Hướng Dẫn Khởi Chạy Local

### 1. Bảng phân bổ cổng mạng (Network Ports)
| Dịch vụ | Địa chỉ Local | Cổng | Ghi chú |
|---|---|---|---|
| **Frontend Web App** | `http://localhost:5173` | **5173** | Giao diện chính cho người dùng |
| **Backend FastAPI** | `http://127.0.0.1:8001` | **8001** | API chính thức (Swagger UI: `/docs`) |
| **PostgreSQL 18** | `127.0.0.1:5434` | **5434** | Container `expense_tracker_db` |
| **pgAdmin 4** | `http://127.0.0.1:5050` | **5050** | Quản trị cơ sở dữ liệu |

> [!NOTE]
> **Vì sao Backend chạy cổng 8001?**
> Cổng 8000 trên máy chủ có thể đang được sử dụng bởi các dịch vụ khác (ví dụ: Badminton AI). Do đó, Backend Quản lý Chi tiêu được chỉ định cổng `8001` để bảo đảm tuyệt đối không gây xung đột mạng và không can thiệp vào các dự án khác.

### 2. Các bước khởi chạy bằng 1 lệnh duy nhất (One-Click Launch)
1. Mở ứng dụng **Docker Desktop** trên máy tính (đảm bảo Docker Engine hiển thị màu xanh - Running).
2. Mở terminal **PowerShell** tại thư mục gốc của dự án:
   ```powershell
   cd "C:\Users\phong\OneDrive\Desktop\Triển khai hệ thống"
   ```
3. Chạy script tự động khởi động:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1
   ```
   *Script sẽ tự động kiểm tra Docker, bật container PostgreSQL 18, bật Backend FastAPI cổng 8001, bật Frontend Vite cổng 5173, kiểm tra Health check và tự động mở trình duyệt.*

### 3. Kiểm tra trạng thái hệ thống bất cứ lúc nào
Người dùng hoặc giảng viên có thể kiểm tra trạng thái sức khỏe của toàn bộ hệ thống bằng lệnh:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_demo.ps1
```

### 4. Nạp dữ liệu mẫu cho buổi thuyết trình (Idempotent Seed Data)
Để có sẵn tài khoản demo có số dư, danh mục và chuỗi giao dịch phong phú:
```powershell
& "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py
```
*Tài khoản demo:*
- **Email:** `demo@expensetracker-demo.com`
- **Mật khẩu:** `DemoPassword123@`

### 5. Cách dừng hệ thống an toàn
- Đóng các cửa sổ terminal Frontend và Backend.
- Nếu muốn dừng container PostgreSQL:
  ```powershell
  docker compose stop db
  ```
- **TUYỆT ĐỐI KHÔNG** chạy `docker compose down -v` để tránh xóa mất dữ liệu trong database.

---

## D. Kịch Bản Trình Diễn Mẫu (Thời Lượng 8 – 12 Phút)

### Bước 1: Đăng nhập & Bảo vệ phiên làm việc (1 phút)
- **Mục đích**: Trình bày tính năng xác thực an toàn, cookie HttpOnly và tự động điều hướng.
- **Thao tác**:
  1. Mở `http://localhost:5173/login`.
  2. Đăng nhập với tài khoản: `demo@expensetracker-demo.com` / `DemoPassword123@`.
- **Kết quả dự kiến**: Đăng nhập thành công, chuyển hướng thẳng vào trang **Tổng quan (Dashboard)**.

### Bước 2: Khám phá Dashboard & Trực quan hóa dòng tiền (1.5 phút)
- **Mục đích**: Thể hiện khả năng tổng hợp tài chính tức thời.
- **Thao tác**: Quan sát các thẻ thống kê: Tổng số dư khả dụng, Tổng thu nhập tháng, Tổng chi tiêu tháng, Dòng tiền thuần (Net cashflow).
- **Kết quả dự kiến**: Các chỉ số hiển thị khớp với số liệu thực tế trong PostgreSQL; biểu đồ phân bổ chi tiêu hiển thị trực quan các danh mục (Ăn uống, Di chuyển...).

### Bước 3: Quản lý Ví Cá Nhân & Ví Chung Gia Đình (1.5 phút)
- **Mục đích**: Thể hiện tính năng đa ví và cách ly phạm vi cá nhân vs. gia đình.
- **Thao tác**:
  1. Vào menu **Ví tiền** (`/accounts`).
  2. Giới thiệu danh sách ví: *Ví Tiền Mặt*, *Tài Khoản Techcombank* và *Quỹ Chung Gia Đình*.
  3. Bấm **Tạo ví mới**: Tạo ví "Tài khoản Tiết kiệm" với số dư ban đầu 5.000.000 VND.
- **Kết quả dự kiến**: Ví mới xuất hiện ngay lập tức, tổng tài sản ở trang Dashboard tự động cộng thêm 5.000.000 VND.

### Bước 4: Thao tác Ghi chép Thu / Chi & Xóa mềm (1.5 phút)
- **Mục đích**: Thể hiện nghiệp vụ thu chi thực tế và tính toàn vẹn của dữ liệu (Soft-delete).
- **Thao tác**:
  1. Vào menu **Giao dịch** (`/transactions`).
  2. Bấm **Thêm giao dịch**: Chọn ví *Ví Tiền Mặt*, loại *Chi tiêu*, danh mục *Ăn uống*, số tiền `150.000 VND`, ghi chú "Ăn trưa cơm văn phòng".
  3. Thử nghiệm chức năng xóa mềm (Soft-delete) một giao dịch cũ và xem số dư ví phục hồi lại tương ứng.
- **Kết quả dự kiến**: Giao dịch ghi nhận tức thì vào PostgreSQL, số dư ví tiền mặt giảm đúng 150.000 VND.

### Bước 5: Chuyển tiền liên ví (Bút toán kép Double-Entry) (1.5 phút)
- **Mục đích**: Trình bày giải pháp kế toán chuẩn: tiền chuyển giữa các ví không bị tính nhầm là chi tiêu hay thu nhập.
- **Thao tác**:
  1. Vào menu **Chuyển tiền** (`/transfers`) hoặc bấm nút **Chuyển tiền** (Transfer Modal).
  2. Chuyển `1.000.000 VND` từ *Tài Khoản Techcombank* sang *Ví Tiền Mặt*, phí chuyển `2.000 VND`.
- **Kết quả dự kiến**: Số dư Techcombank giảm `1.002.000 VND`, số dư Ví Tiền Mặt tăng `1.000.000 VND`, báo cáo Thu/Chi không bị đội thêm 1.000.000 VND doanh thu ảo.

### Bước 6: Quản lý Ngân sách & Cảnh báo vượt ngưỡng (1 phút)
- **Mục đích**: Thể hiện tính năng cảnh báo chi tiêu thông minh.
- **Thao tác**: Vào menu **Ngân sách** (`/budgets`), quan sát ngân sách "Ăn uống" hạn mức 5.000.000 VND với thanh tiến độ hiển thị phần trăm đã chi.
- **Kết quả dự kiến**: Thanh tiến độ đổi màu (xanh -> vàng cảnh báo -> đỏ vượt ngưỡng) khi chi tiêu tiến sát hoặc vượt hạn mức.

### Bước 7: Báo cáo Tài chính & Xuất dữ liệu CSV (1 phút)
- **Mục đích**: Phân tích dòng tiền đa chiều và tính năng trích xuất dữ liệu.
- **Thao tác**:
  1. Vào menu **Báo cáo** (`/reports`).
  2. Chọn xem theo Tháng hiện tại, lọc theo danh mục hoặc theo ví.
  3. Bấm **Xuất file CSV**.
- **Kết quả dự kiến**: Tải về file `.csv` chuẩn định dạng UTF-8-SIG (mở trên Microsoft Excel tiếng Việt không bị lỗi font chữ).

### Bước 8: Giao dịch định kỳ & Trung tâm thông báo (1.5 phút)
- **Mục đích**: Thao tác tự động hóa thu chi định kỳ và thông báo trong ứng dụng.
- **Thao tác**:
  1. Vào menu **Giao dịch định kỳ** (`/recurring-transactions`): Xem quy tắc "Tiền Internet Cáp Quang" đến hạn hôm nay.
  2. Bấm **Tạo giao dịch ngay** cho kỳ này.
  3. Mở **Chuông thông báo** trên thanh điều hướng (`NotificationBell`) hoặc truy cập `/notifications`: Xem các thông báo nhắc nhở đến hạn và cảnh báo ngân sách.
- **Kết quả dự kiến**: Giao dịch tự động ghi nhận vào sổ, số dư ví được khấu trừ chính xác, thông báo tương ứng được tự động lưu trữ (Archived) và không bao giờ sinh giao dịch trùng lặp cho cùng một kỳ.

### Bước 9: Không gian Gia đình & Phân quyền thành viên (1 phút)
- **Mục đích**: Trình bày tính năng cộng tác nhóm và kiểm soát quyền truy cập RBAC (`owner`, `editor`, `viewer`).
- **Thao tác**: Vào menu **Gia đình** (`/families`), giới thiệu không gian "Gia Đình Hạnh Phúc", chức năng mời thành viên và phân quyền vai trò.
- **Kết quả dự kiến**: Thành viên vai trò `viewer` chỉ được xem số dư/giao dịch chung mà không có quyền tạo/sửa giao dịch của gia đình.

---

## E. Bảng Kiểm Tra Nhanh Trước Giờ Báo Cáo (Pre-Demo Checklist)

| Hạng mục kiểm tra | Lệnh xác minh / Thao tác | Trạng thái đạt chuẩn |
|---|---|:---:|
| **1. Docker & PostgreSQL** | `docker ps` | Container `expense_tracker_db` đang chạy trên cổng `5434` |
| **2. Backend Health** | `http://127.0.0.1:8001/health/ready` | Trả về `{"status":"ok","database":"connected"}` |
| **3. Frontend Web** | `http://localhost:5173` | Giao diện mở mượt mà, không bị trắng trang |
| **4. Database Migration** | `alembic current` | Hiển thị `4dc2493f258e (head)` |
| **5. Dữ liệu mẫu demo** | Đăng nhập tài khoản demo | Đăng nhập thành công với `demo@expensetracker-demo.com` |
| **6. Toàn vẹn hệ thống** | `powershell scripts/check_demo.ps1` | Toàn bộ 5 bước đều hiển thị tích xanh `[✓]` |

# Hệ Thống Quản Lý Chi Tiêu Cá Nhân & Gia Đình (Personal & Family Expense Tracker)

Ứng dụng web toàn diện hỗ trợ theo dõi, phân loại và tối ưu hóa tài chính dành cho cá nhân và các nhóm gia đình. Dự án được xây dựng với mục tiêu trở thành **Bản Demo Hoàn Chỉnh** để thuyết trình và đánh giá môn học, kết hợp giao diện hiện đại, nghiệp vụ xử lý dữ liệu thực tế trên PostgreSQL 18 và hạ tầng giám sát chuyên nghiệp.

---

## 1. Công Nghệ Sử Dụng (Tech Stack)

* **Giao diện người dùng (Frontend)**: React, TypeScript, Vite, Modern CSS (Dark/Light mode, Responsive).
* **Giao diện lập trình ứng dụng (Backend)**: Python (FastAPI), SQLAlchemy 2.0 (ORM), Pydantic v2.
* **Cơ sở dữ liệu (Database)**: PostgreSQL 18, pgAdmin 4, Alembic (Database Migrations).
* **Reverse Proxy & Định tuyến**: Nginx.
* **Đóng gói & Điều phối**: Docker & Docker Compose.
* **Hệ thống Giám sát & Nhật ký (Observability Stack)**:
  * **Prometheus**: Thu thập và lưu trữ số liệu (metrics) từ Backend và Nginx.
  * **Grafana Loki**: Thu thập và quản lý nhật ký hệ thống (logs) qua LogQL.
  * **Grafana Alloy**: Bộ thu thập viễn trắc (telemetry collector) gom metrics và logs chuyển tiếp tập trung.
  * **Grafana Dashboard**: Trực quan hóa số liệu hệ thống, cảnh báo và số lượng giao dịch.
* **Kiểm thử & Chất lượng mã nguồn**: Pytest (toàn diện cho backend), Ruff (linter & formatter), TypeScript Compiler (`tsc --noEmit`).

---

## 2. Các Chức Năng Demo Trọng Tâm (Core Demo Features)

1. **Xác thực & Bảo mật**: Đăng ký, đăng nhập cấp Opaque Session Token an toàn, quản lý phiên và thu hồi trong database (`auth_sessions`), đăng xuất.
2. **Quản lý ví tài chính**: Ví tiền mặt, tài khoản ngân hàng, thẻ tín dụng cá nhân và ví chung gia đình; hỗ trợ số dư ban đầu âm/dương.
3. **Quản lý danh mục thu chi**: Danh mục mặc định hệ thống, danh mục cá nhân và gia đình; tổ chức cây phân cấp cha–con linh hoạt.
4. **Sổ giao dịch thu & chi**: Thêm, xem, sửa, lưu trữ hoặc xóa mềm giao dịch; liên kết ví tiền và danh mục tương ứng.
5. **Chuyển tiền liên ví**: Điều phối chuyển tiền giữa 2 ví theo nguyên tắc bút toán kép (`transfers`), xử lý nguyên tử, bảo đảm không bị tính nhầm thành thu nhập/chi tiêu mới trong báo cáo.
6. **Quản lý ngân sách & Cảnh báo**: Thiết lập hạn mức chi tiêu theo danh mục, tính toán tỷ lệ đã dùng và hiển thị cảnh báo khi chạm ngưỡng (80%, 100%).
7. **Dashboard trực quan**: Tổng hợp tổng thu, tổng chi, số dư khả dụng, biểu đồ cơ cấu chi tiêu (Donut chart) và xu hướng dòng tiền (Bar/Area chart).
8. **Không gian gia đình**: Tạo nhóm gia đình, mời thành viên qua email/token bảo mật, phân quyền 3 vai trò (`owner`, `editor`, `viewer`).
9. **Báo cáo tài chính**: Lọc dòng tiền theo khoảng thời gian tùy chọn (tuần, tháng, năm), lọc theo danh mục hoặc thành viên.
10. **Bộ dữ liệu demo có thể reset an toàn**: Script Python sinh sẵn dữ liệu mẫu thực tế (gia đình, ví tiền, các chuỗi giao dịch 3 tháng gần nhất) giúp trình diễn ngay lập tức và có thể đặt lại trạng thái ban đầu bất cứ lúc nào.

---

## 3. Kế Hoạch Triển Khai Demo Theo Giai Đoạn

Chi tiết kế hoạch triển khai và tiêu chí nghiệm thu được tài liệu hóa đầy đủ tại [docs/roadmap.md](docs/roadmap.md):
* **Pha 1**: Hoàn tất tầng dữ liệu (các SQLAlchemy models `Transaction`, `Budget`), migration Alembic và script tạo dữ liệu mẫu.
* **Pha 2**: Xây dựng RESTful APIs FastAPI đầy đủ logic nghiệp vụ (Auth, Accounts, Categories, Transactions, Transfers, Budgets, Families).
* **Pha 3**: Phát triển giao diện React + TypeScript hiện đại, bảng điều khiển và biểu đồ trực quan.
* **Pha 4**: Tích hợp hạ tầng Docker Compose "One-Click Demo" (Nginx, FastAPI, React, PostgreSQL, Prometheus, Grafana, Loki, Grafana Alloy).
* **Pha 5**: Hoàn thiện kịch bản thuyết trình demo và kiểm thử nghiệm thu toàn diện.

---

## 4. Quy Tắc Phát Triển & Chuẩn Mực Mã Nguồn

Vui lòng tham khảo tài liệu [AGENTS.md](AGENTS.md) để nắm rõ các quy định kỹ thuật bắt buộc:
* Không sử dụng mock dữ liệu cho các chức năng nghiệp vụ cốt lõi.
* Không hardcode thông tin nhạy cảm, mật khẩu hoặc secrets ra ngoài file cấu hình môi trường `.env`.
* Kiểm thử là bắt buộc (`pytest`, type checking). Mọi thay đổi phải vượt qua kiểm thử trước khi bàn giao.

---

## 5. Hướng Dẫn Khởi Chạy & Kiểm Thử Cục Bộ (Local Run Guide)

### 5.1. Khởi động Cơ sở dữ liệu PostgreSQL 18
Khởi động container PostgreSQL 18 đã cấu hình trong dự án (Port cục bộ: `5434`):
```powershell
docker compose up -d db
```

### 5.2. Chạy Migration Cơ sở dữ liệu
Áp dụng toàn bộ migration Alembic lên schema mới nhất:
```powershell
& "backend\.venv\Scripts\python.exe" -m alembic -c backend/alembic.ini upgrade head
```

### 5.3. Khởi chạy Backend FastAPI
Backend chạy tại `http://127.0.0.1:8001` (chỉ định cổng 8001 để tránh xung đột với các dịch vụ khác trên cổng 8000):
```powershell
& "backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload
```
* Swagger UI Docs: `http://127.0.0.1:8001/docs`
* Health Check: `http://127.0.0.1:8001/health/ready`

### 5.4. Khởi chạy Frontend React + Vite
Frontend chạy tại `http://localhost:5173`:
```powershell
cd frontend
npm run dev
```

### 5.5. Khởi Chạy Nhanh Cho Buổi Trình Diễn (One-Click Launch & Status Check)
Dự án đã chuẩn hóa sẵn các script PowerShell hỗ trợ khởi động và kiểm tra toàn diện:
```powershell
# 1. Khởi động an toàn toàn bộ hệ thống (Database, Backend, Frontend)
powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1

# 2. Kiểm tra trạng thái sức khỏe toàn diện các dịch vụ
powershell -ExecutionPolicy Bypass -File scripts/check_demo.ps1

# 3. Nạp dữ liệu mẫu an toàn cho buổi thuyết trình (Idempotent Seed Data)
& "backend\.venv\Scripts\python.exe" scripts/seed_demo_data.py
```
*Xem chi tiết kịch bản thuyết trình và hướng dẫn chi tiết tại [docs/demo-guide.md](docs/demo-guide.md).*

### 5.6. Lệnh Kiểm Thử & Kiểm Định Chất Lượng Tự Động
```powershell
# 1. Chạy toàn bộ 165 backend test cases (Pytest)
& "backend\.venv\Scripts\python.exe" -m pytest backend/tests

# 2. Kiểm tra linter Ruff trên backend và scripts
& "backend\.venv\Scripts\python.exe" -m ruff check backend scripts

# 3. Kiểm tra tính toàn vẹn Metadata ORM & Foreign Keys
& "backend\.venv\Scripts\python.exe" scripts/check_model_metadata.py

# 4. Kiểm tra đồng bộ Schema Alembic
& "backend\.venv\Scripts\python.exe" -m alembic -c backend/alembic.ini check

# 5. Chạy kịch bản Kiểm thử chấp nhận End-to-End (6 Luồng xuyên suốt trên PostgreSQL 18)
& "backend\.venv\Scripts\python.exe" scripts/verify_e2e_full_acceptance.py

# 6. Type check và Build Frontend
cd frontend
npm run build
npm run lint
```

---

## 6. Lưu Ý Về Đồng Bộ & Giới Hạn Hệ Thống (Sync & System Notes)

1. **Đồng bộ Thông báo & Khoản Định kỳ (In-App Sync)**:
   * Hệ thống áp dụng cơ chế đồng bộ an toàn theo phiên (On-demand/In-app sync khi người dùng đăng nhập hoặc mở chuông thông báo/trung tâm thông báo), hỗ trợ tính năng chống spam thông báo trùng lặp (Idempotent sync).
   * Không yêu cầu daemon worker nặng nề chạy ngầm gây tốn tài nguyên máy local.
2. **Kênh Thông Báo Hiện Tại**:
   * Hệ thống tập trung tối ưu hóa **In-App Notification Center** (thông báo nội bộ trong ứng dụng qua chuông thông báo, badge đếm tin chưa đọc, modal chi tiết và điều hướng tác vụ).
   * Các kênh thông báo bên ngoài như Email SMTP thực tế hoặc Web Push Notification hiện tại đang ở dạng demo/preview cấu trúc token, sẵn sàng mở rộng khi tích hợp dịch vụ bên thứ ba.

---

## 7. Hệ Thống Giám Sát (Monitoring & Observability)

Dự án tích hợp sẵn hệ thống giám sát thời gian thực với **Prometheus**, **Grafana** và **PostgreSQL Exporter** chạy hoàn toàn trên Docker Compose:

### 7.1. Khởi động các dịch vụ giám sát
```powershell
docker compose up -d postgres-exporter prometheus grafana
```

Kiểm tra trạng thái các container:
```powershell
docker compose ps
```

### 7.2. Truy cập & Thông tin đăng nhập
* **Prometheus Web UI**: `http://127.0.0.1:9090`
  * Kiểm tra targets đang cào dữ liệu: `http://127.0.0.1:9090/targets` (cả `prometheus` và `postgres-exporter` ở trạng thái **UP**).
* **Grafana Dashboard**: `http://127.0.0.1:3000`
  * **Tài khoản mặc định**: `admin`
  * **Mật khẩu**: Lấy từ biến môi trường `GRAFANA_ADMIN_PASSWORD` trong file `.env` (mặc định mẫu: `example_grafana_password_replace_in_env`).
  * **Datasource tự động (Provisioned)**: Prometheus (`http://prometheus:9090`).
  * **Dashboard dựng sẵn**: *Expense Tracker — PostgreSQL & System Metrics* (UID: `expense-tracker-db-metrics`), bao gồm:
    * Trạng thái kết nối PostgreSQL (`pg_up`).
    * Số lượng kết nối hoạt động và phân bổ theo trạng thái (`pg_stat_activity_count`).
    * Tốc độ giao dịch Commit / Rollback (`pg_stat_database_xact_commit`, `pg_stat_database_xact_rollback`).
    * Dung lượng database `expense_tracker` theo thời gian (`pg_database_size_bytes`).
    * Thời gian hoạt động liên tục (Uptime) của PostgreSQL Server.
* **pgAdmin 4**: `http://127.0.0.1:5050`
  * Đăng nhập với `PGADMIN_DEFAULT_EMAIL` và `PGADMIN_DEFAULT_PASSWORD` từ `.env`.

### 7.3. Xử lý sự cố thường gặp (Troubleshooting)
1. **Target `postgres-exporter` hiển thị DOWN trong Prometheus**:
   * Kiểm tra container PostgreSQL có đang chạy và healthy không: `docker compose ps db`.
   * Kiểm tra log của exporter: `docker compose logs postgres-exporter --tail 50`.
   * Đảm bảo chuỗi kết nối sử dụng hostname nội bộ `db:5432`, không dùng `localhost` hay IP host.
2. **Grafana không hiển thị biểu đồ hoặc báo lỗi kết nối datasource**:
   * Kiểm tra mạng Docker `app-network` có thông suốt giữa Grafana và Prometheus không.
   * Kiểm tra log Grafana: `docker compose logs grafana --tail 50`.
   * Thử test query trực tiếp trên Prometheus: `http://127.0.0.1:9090/graph?g0.expr=pg_up`.


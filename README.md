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

## 7. Hệ Thống Giám Sát & Nhật Ký (Full Observability Stack)

Dự án tích hợp đầy đủ 4 trụ cột giám sát thời gian thực với **Prometheus**, **Grafana**, **Loki**, **Grafana Alloy**, **Blackbox Exporter**, **PostgreSQL Exporter** và **Nginx Reverse Proxy** chạy hoàn toàn trên Docker Compose:

### 7.1. Khởi động toàn bộ các dịch vụ giám sát & proxy
```powershell
docker compose up -d db pgadmin postgres-exporter prometheus loki alloy blackbox-exporter nginx nginx-exporter grafana
```

Kiểm tra trạng thái các container:
```powershell
docker compose ps
```

### 7.2. Danh sách dịch vụ & Cổng truy cập (Host Ports)
* **Grafana Dashboard**: `http://127.0.0.1:3000`
  * **Tài khoản**: `admin` / Mật khẩu lấy từ `GRAFANA_ADMIN_PASSWORD` trong `.env`.
  * **Datasources (Provisioned)**: Prometheus (`http://prometheus:9090`) và Loki (`http://loki:3100`).
  * **Dashboards dựng sẵn**:
    1. *Expense Tracker — System Monitoring Dashboard* (UID: `expense-tracker-system-overview`): Bố cục tổng quan chuẩn mẫu bao gồm Container count, Backend/DB/Nginx status, RAM & CPU cAdvisor charts, FastAPI request rate & latency, Blackbox probe health, DB & Nginx metrics và nhật ký Loki.
    2. *Expense Tracker — PostgreSQL, Backend, Nginx & Loki Metrics* (UID: `expense-tracker-db-metrics`): Bảng điều khiển chi tiết cơ sở dữ liệu và hệ thống.
* **cAdvisor (Container Monitoring)**: `http://127.0.0.1:9080` (Metrics: `http://cadvisor:8080/metrics`).
* **Prometheus Web UI**: `http://127.0.0.1:9090`
  * Kiểm tra targets cào số liệu tại: `http://127.0.0.1:9090/targets` (tất cả targets đều `UP`).
* **Grafana Loki (Log Ingestion & Query)**: `http://127.0.0.1:3100` (Kiểm tra ready: `http://127.0.0.1:3100/ready`).
* **Grafana Alloy (Log Collector UI)**: `http://127.0.0.1:12345` (Thu thập stdout/stderr Docker container qua Docker socket và chuyển tiếp về Loki).
* **Blackbox Exporter (Health & Probe)**: `http://127.0.0.1:9115` (Kiểm tra HTTP availability của `/health/live`, `/health/ready` và `/health`).
* **Nginx Reverse Proxy**: `http://127.0.0.1:8088` (Proxy `/api/` tới FastAPI Backend và mở `/stub_status` nội bộ cho exporter).
* **Nginx Prometheus Exporter**: `http://127.0.0.1:9113/metrics`.
* **PostgreSQL Exporter**: Cổng nội bộ container `9187` kết nối `db:5432`.
* **pgAdmin 4**: `http://127.0.0.1:5050`.

### 7.3. Xử lý sự cố thường gặp (Troubleshooting)
1. **Target `backend` hiển thị DOWN trong Prometheus**:
   * Kiểm tra xem Backend FastAPI đã được khởi động chưa:
     ```powershell
     & "backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8001
     ```
   * Lưu ý sử dụng `--host 0.0.0.0` để container Docker có thể kết nối thông qua `host.docker.internal:8001`.
2. **Loki báo 503 Ingester not ready khi vừa khởi động**:
   * Loki cấu hình single-binary cần khoảng 15 giây sau khi bật để hoàn tất vòng khởi tạo in-memory ring. Sau 15 giây, endpoint `http://127.0.0.1:3100/ready` sẽ trả về `200 ready`.
3. **Blackbox Exporter báo `probe_success = 0` cho host.docker.internal**:
   * Cấu hình trong `monitoring/blackbox/blackbox.yml` đã được tối ưu hóa `preferred_ip_protocol: "ip4"` để tương thích hoàn hảo với gateway Docker Desktop trên Windows.
4. **Cổng 8080 bị chiếm dụng bởi service khác**:
   * Cổng host của Nginx được cấu hình sang `127.0.0.1:8088:80` để tuyệt đối không xung đột với cổng `8080` hay cổng `8000` của các ứng dụng khác.


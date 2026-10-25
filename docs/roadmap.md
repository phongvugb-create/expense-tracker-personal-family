# Lộ Trình Phát Triển & Bản Kế Hoạch Demo (Demo-Focused Roadmap)

Tài liệu này xác định lộ trình phát triển định hướng **Bản Demo Hoàn Chỉnh (Working Capstone / Course Assessment Demo)** cho Hệ thống Quản lý Chi tiêu Cá nhân & Gia đình. Mục tiêu cốt lõi là tạo ra một sản phẩm phần mềm chuyên nghiệp, giao diện hiện đại, nghiệp vụ chạy thật trên PostgreSQL 18, đầy đủ các thành phần hạ tầng (Docker, Nginx, Prometheus, Grafana, Loki, Grafana Alloy) để sẵn sàng trình diễn, chấm điểm và đánh giá kỹ thuật.

---

## 1. Mục Tiêu & Nguyên Tắc Cốt Lõi của Bản Demo

1. **Nghiệp vụ chạy thật 100% (Real End-to-End Execution)**:
   * Tất cả chức năng demo đều phải kết nối thật giữa **React Frontend**, **FastAPI Backend**, và **PostgreSQL Database**.
   * Tuyệt đối không sử dụng mock dữ liệu tạm thời hoặc trả về dữ liệu tĩnh ở backend để giả lập chức năng đã hoàn thành.
2. **Dữ liệu Demo & Script Reset An Toàn**:
   * Cung cấp kịch bản sinh dữ liệu mẫu (`seed data script`) phục vụ thuyết trình trực quan (có sẵn các giao dịch thu chi mẫu, ví tiền cá nhân/gia đình, ngân sách, biểu đồ sinh động).
   * Dữ liệu demo phải được tách biệt rõ ràng, có khả năng reset về trạng thái ban đầu một cách an toàn mà không làm mất cấu trúc hệ thống.
3. **Giữ Vững Tiêu Chuẩn Kỹ Thuật & Giám Sát**:
   * Không bỏ qua xác thực bảo mật (Opaque Session Token lưu hash trong database, có thời hạn và hỗ trợ thu hồi tức thì), phân quyền dữ liệu (Personal vs. Family data isolation), và tính chính xác tuyệt đối của số liệu tài chính (`Numeric(15, 2)`).
   * Mọi container trong Docker Compose phải hoạt động ổn định, kèm hạ tầng quan sát (Observability: Prometheus, Grafana, Loki, Grafana Alloy) và Reverse Proxy (Nginx) hoạt động trực tiếp trên máy local/lab mà không bắt buộc phải mua VPS hay tên miền bên ngoài.
4. **Tránh Overengineering (Phòng ngừa phức tạp hóa không cần thiết)**:
   * Tập trung nguồn lực hoàn thiện 10 chức năng demo trọng tâm thay vì xây dựng các tính năng ngoài lề quy mô lớn chưa cần cho buổi báo cáo.

---

## 2. Danh Mục 10 Chức Năng Demo Bắt Buộc (Core Demo Deliverables)

| STT | Chức Năng Demo | Mô Tả & Tiêu Chí Đánh Giá Nghiệp Vụ | Trạng Thái Hạ Tầng / Model Hiện Tại |
|:---:|---|---|---|
| **1** | **Xác thực Người Dùng** (Auth Flow) | Đăng ký tài khoản, đăng nhập cấp Opaque Session Token (entropy cao, database chỉ lưu hash), quản lý phiên `auth_sessions`, thu hồi tức thì và đăng xuất. Phân biệt người dùng cá nhân. | Đã hoàn tất 100% models: `User`, `AuthSession`, `EmailVerificationToken`, `PasswordResetToken`. Sẵn sàng viết API Auth. |
| **2** | **Quản Lý Ví Cá Nhân & Gia Đình** (Wallets / Accounts) | Tạo ví cá nhân (tiền mặt, ngân hàng, thẻ tín dụng) và ví dùng chung gia đình. Số dư khởi tạo, biểu tượng, loại tiền tệ (VND). | Đã hoàn tất 100% model `Account` với ràng buộc loại trừ phạm vi (`scope_ownership`). |
| **3** | **Quản Lý Danh Mục Thu Chi** (Categories) | Danh mục hệ thống mặc định, danh mục cá nhân tùy biến, danh mục gia đình. Hỗ trợ cấu trúc cây phân cấp (cha - con). | Đã hoàn tất 100% model `Category` tự tham chiếu an toàn. |
| **4** | **Quản Lý Giao Dịch Thu & Chi** (Transactions) | Thêm, xem, sửa, xóa mềm và lưu trữ giao dịch thu nhập/chi phí. Gắn vào ví tiền và danh mục tương ứng. | Đã hoàn tất 100% model `Transaction` với đầy đủ các ràng buộc hạch toán. |
| **5** | **Chuyển Tiền Giữa Các Ví** (Transfers) | Chuyển khoản nội bộ giữa 2 ví (cùng chủ quyền sở hữu). Sinh bút toán kép nguyên tử (`transfer_out` & `transfer_in`), không tính nhầm thành thu/chi mới. | Đã hoàn tất 100% model `Transfer` với ràng buộc 2 ví khác nhau và phí chuyển. |
| **6** | **Quản Lý Ngân Sách & Cảnh Báo** (Budgets & Alerts) | Thiết lập ngân sách theo danh mục (tháng/tuần). Tính toán tỷ lệ đã chi tiêu và hiển thị cảnh báo trực quan khi chạm ngưỡng (80%, 100%). | Đã hoàn tất 100% model `Budget` và logic đối soát ngân sách. |
| **7** | **Dashboard Tổng Quan Tài Chính** (Dashboard & Charts) | Màn hình chính tổng hợp: Tổng thu, tổng chi, tổng tài sản thuần, biến động số dư theo thời gian, biểu đồ cơ cấu chi tiêu dạng Donut/Bar. | Yêu cầu API tổng hợp dữ liệu và React UI charts đẹp mắt. |
| **8** | **Quản Lý Nhóm Gia Đình & Phân Quyền** (Family Workspace) | Tạo gia đình, mời thành viên qua email/token, phân quyền vai trò (`owner`, `editor`, `viewer`). Kiểm soát dữ liệu ví/chi tiêu chung. | Đã hoàn tất 100% models: `Family`, `FamilyMember`, `FamilyInvitation`. |
| **9** | **Báo Cáo Thu Chi & Lọc Dữ Liệu** (Financial Reports) | Báo cáo dòng tiền theo khoảng thời gian tùy chọn (tuần, tháng, năm), lọc theo danh mục, ví tiền, hoặc thành viên chi tiêu. | API lọc linh hoạt theo thời gian và hiển thị bảng biểu/biểu đồ. |
| **10** | **Kịch Bản & Bộ Dữ Liệu Demo** (Demo Seed Script) | Script Python/SQL khởi tạo sẵn 1 gia đình hoàn chỉnh (bố, mẹ, con), ví tiền, danh mục, chuỗi giao dịch 3 tháng gần nhất để demo ngay lập tức. | Sẽ triển khai sau khi hoàn tất migration. |

---

## 3. Lộ Trình Triển Khai Chi Tiết (Phased Implementation Plan)

### Pha 1: Hoàn Tất Tầng Dữ Liệu & Database Migrations (Backend Data Foundation)
* **Nhiệm vụ 1.1**: Rà soát tính nhất quán của toàn bộ 12 SQLAlchemy models, mapper configurations và PostgreSQL DDL compilation (ĐÃ HOÀN TẤT).
* **Nhiệm vụ 1.2**: Cấu hình Alembic database migrations.
  * Sinh file migration ban đầu chứa toàn bộ 12 bảng và ràng buộc chuẩn PostgreSQL 18.
  * Chạy `alembic upgrade head` trên container PostgreSQL `expense_tracker_db`.
* **Nhiệm vụ 1.3**: Viết script `seed_demo_data.py` để nạp dữ liệu mẫu sinh động phục vụ thuyết trình và hỗ trợ lệnh reset sạch sẽ.

---

### Pha 2: Xây Dựng RESTful APIs & Logic Nghiệp Vụ (FastAPI Core Services)
* **Nhiệm vụ 2.1 - Auth & User API**:
  * Endpoints: Đăng ký (`/auth/register`), Đăng nhập (`/auth/login`), Đăng xuất (`/auth/logout`), Lấy hồ sơ (`/auth/me`).
  * Opaque Session Token (kết hợp Bearer header) và quản lý phiên trong `auth_sessions`.
* **Nhiệm vụ 2.2 - Wallets & Accounts API**:
  * CRUD ví tiền cá nhân và gia đình.
  * Tính toán số dư khả dụng động (không lưu cứng balance).
* **Nhiệm vụ 2.3 - Categories API**:
  * Lấy cây danh mục (hệ thống + cá nhân + gia đình), thêm/sửa danh mục.
* **Nhiệm vụ 2.4 - Transactions & Transfers API**:
  * Ghi nhận giao dịch thu/chi, phân trang, lọc theo thời gian.
  * Giao dịch chuyển tiền liên ví với xử lý nguyên tử (Atomic Database Transaction).
* **Nhiệm vụ 2.5 - Budgets & Alerts API**:
  * Thiết lập ngân sách, API kiểm tra tiến độ chi tiêu và trạng thái cảnh báo vượt ngưỡng.
* **Nhiệm vụ 2.6 - Family Management API**:
  * Tạo nhóm gia đình, danh sách thành viên, gửi và chấp nhận lời mời.
* **Nhiệm vụ 2.7 - Analytics & Dashboard API**:
  * Tổng hợp thu chi, phân bổ chi tiêu theo danh mục, dòng tiền theo tuần/tháng.

---

### Pha 3: Xây Dựng Giao Diện Người Dùng (Modern React + TypeScript Frontend)
* **Nhiệm vụ 3.1 - Scaffolding & Design System**:
  * Khởi tạo React 18 + Vite + TypeScript với CSS hiện đại (Dark mode sang trọng, bố cục gọn gàng, responsive).
  * Cấu hình Axios API client, Authentication Context, Protected Routes.
* **Nhiệm vụ 3.2 - Màn hình Xác thực & Hồ Sơ**:
  * Login, Register, User Profile.
* **Nhiệm vụ 3.3 - Màn hình Dashboard Tổng Quan (Trọng tâm Demo)**:
  * Thẻ tổng quan tài sản (Tổng số dư, Tổng thu trong tháng, Tổng chi, Tỷ lệ tiết kiệm).
  * Biểu đồ chi tiêu theo danh mục (Pie/Donut Chart).
  * Biểu đồ dòng tiền thu chi theo ngày/tháng (Bar/Area Chart).
  * Danh sách giao dịch gần nhất và cảnh báo ngân sách nguy cấp.
* **Nhiệm vụ 3.4 - Màn hình Quản Lý Ví & Chuyển Tiền**:
  * Thẻ ví cá nhân và ví gia đình trực quan.
  * Modal giao dịch chuyển tiền giữa 2 ví với phản hồi số dư tức thì.
* **Nhiệm vụ 3.5 - Màn hình Sổ Giao Dịch & Quản Lý Ngân Sách**:
  * Bộ lọc giao dịch theo ngày, ví, danh mục. Modal thêm giao dịch nhanh.
  * Thanh tiến độ ngân sách trực quan (xanh: an toàn, vàng: chạm ngưỡng cảnh báo, đỏ: vượt ngân sách).
* **Nhiệm vụ 3.6 - Màn hình Quản Lý Nhóm Gia Đình**:
  * Danh sách thành viên, vai trò, lời mời gia nhập, chuyển đổi không gian làm việc (Personal vs. Family).

---

### Pha 4: Tích Hợp Hệ Thống Giám Sát, Reverse Proxy & Đóng Gói Demo (Full-Stack Showcase)
* **Nhiệm vụ 4.1 - Nginx Reverse Proxy**:
  * Cấu hình Nginx điều phối toàn bộ traffic: `/` trỏ đến Frontend SPA, `/api/` trỏ đến FastAPI Backend, `/metrics` bảo vệ an toàn.
* **Nhiệm vụ 4.2 - Giám Sát & Nhật Ký (Observability Demo)**:
  * Bật `prometheus-fastapi-instrumentator` để thu thập metrics HTTP request, latency.
  * Cấu hình Prometheus cào metrics backend và Nginx.
  * Cấu hình Grafana Alloy thu thập log backend và đẩy về Grafana Loki.
  * Tạo sẵn Dashboard Grafana mẫu trực quan hóa hiệu năng hệ thống và số lượng giao dịch.
* **Nhiệm vụ 4.3 - Đóng Gói Docker Compose "One-Click Demo"**:
  * Điều phối toàn bộ 7 containers trong `docker-compose.yml`:
    * `db` (PostgreSQL 18)
    * `pgadmin` (pgAdmin 4)
    * `backend` (FastAPI)
    * `frontend` (React + Vite)
    * `nginx` (Reverse Proxy)
    * `prometheus` & `grafana` & `loki` & `alloy` (Observability)
  * Kiểm thử lệnh chạy duy nhất: `docker compose up -d` là toàn bộ hệ thống sẵn sàng hoạt động.

---

### Pha 5: Kịch Bản Thuyết Trình & Kiểm Thử Nghiệm Thu (Presentation & Testing)
* **Nhiệm vụ 5.1 - Unit & Integration Testing**:
  * Bộ test `pytest` bao phủ toàn bộ models, services và API endpoints chính.
  * Type check frontend với `tsc --noEmit`.
* **Nhiệm vụ 5.2 - Kịch Bản Trình Bày Demo (Demo Walkthrough Guide)**:
  * Soạn tài liệu hướng dẫn từng bước cho người thuyết trình (kịch bản 10 - 15 phút từ login, chuyển đổi ví, thêm giao dịch, xem cảnh báo ngân sách, đến mở Grafana kiểm tra log và metrics).

# AGENTS.md - Quy định Phát triển Dự án Quản lý Chi tiêu Cá nhân & Gia đình

Tài liệu này định nghĩa các nguyên tắc kỹ thuật, kiến trúc, quy chuẩn mã nguồn và quy trình làm việc bắt buộc dành cho mọi AI Agent và lập trình viên khi tham gia xây dựng hệ thống.

---

## 1. Công nghệ Sử dụng (Tech Stack)

* **Frontend**: React, TypeScript, Vite, CSS / Modern Styling.
* **Backend**: Python, FastAPI, SQLAlchemy 2.0 (Async/Sync ORM), Alembic (Database Migrations).
* **Cơ sở dữ liệu**: PostgreSQL.
* **Containerization & Reverse Proxy**: Docker, Docker Compose, Nginx (Reverse Proxy & Static Asset Serving).
* **Monitoring & Observability**:
  * **Metrics**: Prometheus (thu thập metrics từ FastAPI & Nginx qua `/metrics`).
  * **Logs**: Grafana Loki (lưu trữ và truy vấn log).
  * **Telemetry & Collector**: Grafana Alloy (thu thập metrics, traces và logs chuyển tiếp về Prometheus & Loki).
  * **Visualization**: Grafana (dashboards theo dõi hệ thống, chi tiêu và alert).

---

## 2. Quy tắc Bắt buộc (Core Rules)

1. **Không ghi đè code chưa kiểm tra**:
   * Mọi sửa đổi phải được kiểm tra tính tương thích với code hiện hữu trước khi ghi đè hoặc commit.
2. **Không hardcode mật khẩu hoặc secrets**:
   * Tất cả thông tin nhạy cảm (DB passwords, secret keys, JWT secret, API tokens) phải lưu trong file `.env` và truy xuất qua biến môi trường.
   * Cung cấp `.env.example` với giá trị mẫu an toàn; file `.env` thật phải nằm trong `.gitignore`.
3. **Không dùng dữ liệu giả thay cho chức năng thật**:
   * Không được "mock" kết quả trả về tạm thời để giả vờ hoàn thành chức năng.
   * Mọi API và chức năng phải được cài đặt logic nghiệp vụ thực tế kết nối với cơ sở dữ liệu PostgreSQL.
4. **Không bỏ qua kiểm thử (Testing is Mandatory)**:
   * Backend phải có Unit Test / Integration Test với `pytest`.
   * Frontend phải có kiểm tra type với TypeScript compiler (`tsc --noEmit`) và component tests.
   * Mọi endpoint và migration phải chạy thử thành công trước khi coi là hoàn thành.
5. **Không tự ý xóa file hoặc sửa module ngoài phạm vi**:
   * Chỉ thao tác chính xác trên các file/module được yêu cầu trong phạm vi nhiệm vụ.
   * Không tự ý xóa file cũ hoặc refactor các module không liên quan khi chưa có yêu cầu rõ ràng.
6. **Xử lý lỗi và kiểm tra quyền truy cập (Error Handling & Authorization)**:
   * Mọi endpoint đều phải bắt lỗi có cấu trúc, trả về mã HTTP thích hợp (400, 401, 403, 404, 422, 500) kèm thông điệp rõ ràng.
   * Mọi dữ liệu chi tiêu (cá nhân vs. gia đình) phải được kiểm tra quyền truy cập chặt chẽ: người dùng chỉ được xem/sửa chi tiêu của chính mình hoặc nhóm gia đình mà mình là thành viên hợp lệ.
7. **Báo cáo sau mỗi nhiệm vụ**:
   * Sau khi hoàn thành bất kỳ nhiệm vụ nào, bắt buộc phải báo cáo:
     * Danh sách các file đã tạo hoặc thay đổi (kèm đường dẫn).
     * Kết quả thực thi kiểm thử và lệnh xác minh đã chạy.

---

## 2.1. Định Hướng & Phạm Vi Demo (Demo Scope)

Dự án hiện đang tập trung phát triển **Bản Demo Hoàn Chỉnh** để trình diễn và đánh giá đồ án/môn học:
* **Mục tiêu cốt lõi**: Tạo ra một sản phẩm chạy thực tế 100% (End-to-End), giao diện chuyên nghiệp, nghiệp vụ chính xác, PostgreSQL lưu dữ liệu thật, và hạ tầng (Docker Compose, Nginx, Prometheus, Grafana, Loki, Grafana Alloy) sẵn sàng hoạt động trên máy local/lab.
* **10 Chức năng demo bắt buộc**:
  1. Xác thực (Đăng ký, Đăng nhập JWT, Đăng xuất, Session).
  2. Quản lý ví cá nhân và ví gia đình (hỗ trợ số dư ban đầu, phân loại ví).
  3. Quản lý danh mục thu chi (phân cấp cha-con, phạm vi system/personal/family).
  4. Quản lý giao dịch thu chi (thêm, xem, sửa, lưu trữ/xóa mềm).
  5. Chuyển tiền giữa các ví (nguyên tắc bút toán kép, xử lý nguyên tử, không làm sai lệch báo cáo thu chi).
  6. Quản lý ngân sách & cảnh báo chi tiêu vượt ngưỡng.
  7. Dashboard tổng quan tài chính (tổng thu, chi, số dư khả dụng, biểu đồ cơ cấu và xu hướng).
  8. Không gian gia đình (quản lý thành viên, lời mời, phân quyền vai trò owner/editor/viewer).
  9. Báo cáo dòng tiền theo thời gian và danh mục.
  10. Bộ script tạo dữ liệu mẫu (`seed data script`) phục vụ thuyết trình và có khả năng reset an toàn.
* **Nguyên tắc kỹ thuật**:
  * Tuyệt đối không dùng mock hoặc dữ liệu tĩnh để giả lập chức năng nghiệp vụ đã hoàn thành.
  * Tránh overengineering: Tập trung nguồn lực hoàn thiện 10 chức năng demo nói trên; không phát triển các tính năng ngoài lề quy mô lớn chưa cần thiết cho buổi báo cáo.
  * Không bắt buộc mua VPS hay tên miền bên ngoài; toàn bộ hệ thống phải chạy mượt mà qua Docker Compose trên máy cục bộ.
  * Giữ nguyên mọi quy tắc bảo mật mật khẩu, JWT secret trong `.env`, kiểm thử tự động bắt buộc và kiểm soát quyền truy cập dữ liệu cá nhân vs. gia đình.

---

## 3. Kiến trúc Thư mục Đề xuất

```text
├── .agents/
│   └── rules/                  # Các rule chi tiết bổ trợ nếu có
├── backend/
│   ├── app/
│   │   ├── api/                # Router và endpoints (v1)
│   │   ├── core/               # Config, security, database session
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas (Request/Response)
│   │   ├── services/           # Nghiệp vụ xử lý (Business logic)
│   │   └── main.py             # FastAPI entrypoint & metrics exporter
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Màn hình ứng dụng (Dashboard, Wallets, Transactions...)
│   │   ├── services/           # API client (Axios/Fetch)
│   │   ├── types/              # TypeScript interfaces/types
│   │   └── App.tsx
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── nginx/
│   ├── nginx.conf              # Reverse proxy định tuyến frontend & backend
│   └── Dockerfile
├── monitoring/
│   ├── prometheus/             # prometheus.yml
│   ├── alloy/                  # config.alloy (Grafana Alloy collector)
│   ├── loki/                   # loki-config.yml
│   └── grafana/                # Dashboards & datasources provisioning
├── docker-compose.yml          # Điều phối toàn bộ stack
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

---

## 4. Quy chuẩn Mã nguồn & Kiểm thử

### Backend (FastAPI + SQLAlchemy + Alembic)
* Sử dụng Pydantic v2 cho validation dữ liệu.
* Quản lý phiên bản cơ sở dữ liệu hoàn toàn qua Alembic (`alembic revision --autogenerate -m "..."` và `alembic upgrade head`).
* Tích hợp logging chuẩn có timestamp, level, module name để Grafana Alloy / Loki phân tích.
* Expose `/metrics` cho Prometheus thông qua middleware (ví dụ `prometheus-fastapi-instrumentator`).

### Frontend (React + TypeScript)
* Strict mode TypeScript bật sẵn, không sử dụng `any` bừa bãi.
* Quản lý trạng thái rõ ràng, xử lý đầy đủ các trạng thái UI: `Loading`, `Error`, `Empty Data`, `Success`.
* Tương thích hoàn toàn trên Desktop và Mobile (Responsive Design).

### Giám sát & Vận hành (Observability)
* Mọi dịch vụ chạy trên Docker Compose phải có cấu hình `healthcheck` phù hợp.
* Grafana Alloy gom log và metrics tập trung, đảm bảo không làm gián đoạn hiệu năng của app chính.

# BÁO CÁO TỔNG KẾT ĐỒ ÁN
# HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN VÀ GIA ĐÌNH (EXPENSE TRACKER)

---

## 1. Giới thiệu đề tài
- **Tên đề tài**: Xây dựng Hệ thống Quản lý Chi tiêu Cá nhân và Gia đình (Personal & Family Expense Tracker).
- **Mục đích**: Cung cấp giải pháp phần mềm quản lý tài chính toàn diện, bảo mật và minh bạch, phục vụ đồng thời nhu cầu theo dõi thu chi cá nhân và quản lý ngân quỹ chung của các thành viên trong gia đình.
- **Nền tảng công nghệ**:
  - **Frontend**: React 19, TypeScript, Vite, Vanilla CSS với hệ thống Design Tokens Fresh Family Finance.
  - **Backend**: Python 3.14 / FastAPI, Pydantic v2.
  - **Cơ sở dữ liệu & ORM**: PostgreSQL 18, SQLAlchemy 2.0 (mapped models), Alembic migrations.
  - **Môi trường triển khai**: Docker & Docker Compose (cách ly dịch vụ cục bộ).

---

## 2. Bối cảnh và vấn đề cần giải quyết
1. **Thiếu tính năng tách biệt giữa chi tiêu cá nhân và gia đình**: Phần lớn các ứng dụng hiện nay chỉ hỗ trợ sổ ghi chép đơn lẻ cho một người dùng. Khi cần đóng góp sinh hoạt phí gia đình, người dùng phải tính toán thủ công hoặc ghi chép chồng chéo.
2. **Sai lệch số dư khi chuyển tiền giữa các tài khoản**: Nhiều ứng dụng coi thao tác chuyển tiền (Transfer) là một khoản "chi tiêu" ở ví nguồn và "thu nhập" ở ví đích, dẫn đến báo cáo tài chính cuối tháng bị phóng đại dòng tiền ảo.
3. **Bảo mật và rò rỉ dữ liệu tài chính**: Việc lưu trữ token không an toàn (như lưu access token trong `localStorage` dẫn đến nguy cơ tấn công XSS) hoặc không có cơ chế thu hồi phiên tức thời gây mất an toàn thông tin nhạy cảm.
4. **Vấn đề theo dõi các khoản định kỳ**: Tiền điện, nước, internet, học phí, tiền thuê nhà thường bị quên hoặc đóng trễ nếu không có cơ chế tự động tính toán kỳ đến hạn và nhắc nhở.

---

## 3. Mục tiêu tổng quát và mục tiêu cụ thể
- **Mục tiêu tổng quát**: Xây dựng một ứng dụng web hoạt động thực tế 100% (End-to-End), lưu trữ dữ liệu thật trên PostgreSQL, không dùng dữ liệu giả định (mock), có giao diện người dùng chuyên nghiệp, thân thiện và độ tin cậy cao.
- **Mục tiêu cụ thể**:
  1. Xây dựng cơ chế xác thực an toàn bằng Opaque Session Token lưu trong HttpOnly Cookie, bảo vệ mật khẩu bằng thuật toán Argon2id.
  2. Quản lý đa tài khoản/ví (tiền mặt, thẻ ngân hàng, ví điện tử) theo 2 phạm vi: Cá nhân (`personal`) và Gia đình (`family`).
  3. Cài đặt nghiệp vụ chuyển tiền theo nguyên tắc **bút toán kép (Double-Entry Bookkeeping)**, bảo toàn số dư thực tế và hỗ trợ phí giao dịch.
  4. Quản lý ngân sách theo tháng, tính toán tỷ lệ chi tiêu thực tế và cảnh báo vượt ngưỡng (80%, 100%).
  5. Cung cấp báo cáo dòng tiền, cơ cấu chi tiêu và hỗ trợ xuất dữ liệu ra file CSV theo chuẩn RFC 4180.
  6. Xây dựng vòng đời giao dịch định kỳ (Recurring Transactions) và Trung tâm thông báo (Notifications Center).

---

## 4. Phạm vi chức năng (10 Chức năng demo cốt lõi)
Hệ thống hiện đã hoàn thiện đầy đủ 10 phân hệ nghiệp vụ chính:
1. **Xác thực người dùng (Authentication)**: Đăng ký tài khoản, Đăng nhập phiên bảo mật, Đăng xuất thu hồi phiên, Lấy thông tin phiên hiện tại (`/api/v1/auth/me`).
2. **Quản lý ví tài khoản (Accounts)**: Tạo ví với số dư ban đầu, phân loại loại ví (Cash, Bank, E-wallet), phân định phạm vi ví cá nhân vs. ví dùng chung gia đình, lưu trữ/xóa mềm.
3. **Danh mục thu chi (Categories)**: Cây danh mục 2 cấp (cha - con), phân chia phạm vi (Hệ thống, Cá nhân, Gia đình), lọc theo loại Thu/Chi.
4. **Sổ giao dịch (Transactions)**: Thêm mới, xem chi tiết, chỉnh sửa, xóa mềm (soft-delete), phân trang, lọc đa tiêu chí (ngày tháng, ví, danh mục).
5. **Chuyển tiền giữa các ví (Transfers)**: Chuyển khoản nội bộ giữa 2 ví, xử lý phí chuyển tiền, hủy hiệu lực giao dịch chuyển tiền (Void transfer) hoàn trả số dư nguyên tử.
6. **Ngân sách & Cảnh báo (Budgets)**: Thiết lập hạn mức chi tiêu theo danh mục và tháng, tính % chi tiêu thực tế từ các giao dịch hợp lệ, cảnh báo trạng thái an toàn / cảnh báo / vượt hạn mức.
7. **Bảng điều khiển tài chính (Dashboard)**: Thống kê số dư khả dụng, tổng thu, tổng chi, dòng tiền thuần, biểu đồ đối sánh xu hướng 6 tháng kèm tooltip chi tiết và cơ cấu chi tiêu.
8. **Không gian gia đình (Families)**: Tạo nhóm gia đình, mời thành viên qua mã mời/link mời có hạn sử dụng, phân quyền vai trò.
9. **Báo cáo dòng tiền (Reports)**: Tổng hợp dòng tiền theo thời gian, đối sánh kỳ này với kỳ trước, cơ cấu chi tiêu và xuất báo cáo CSV có BOM UTF-8.
10. **Giao dịch định kỳ & Thông báo (Recurring & Notifications)**: Quy tắc lặp định kỳ (Hàng ngày, Hàng tuần, Hàng tháng, Hàng năm), tự động tính kỳ đến hạn, phát sinh giao dịch tự động chống trùng lặp, chuông thông báo nổi và trang quản lý thông báo.

---

## 5. Đối tượng sử dụng và Phân quyền (RBAC)

### 5.1. Không gian Cá nhân (Personal Scope)
- Người dùng có toàn quyền sở hữu, tạo, sửa, xóa các ví cá nhân, danh mục cá nhân và giao dịch cá nhân.
- Dữ liệu cá nhân được cách ly hoàn toàn giữa các tài khoản người dùng khác nhau qua điều kiện `user_id = current_user.id`.

### 5.2. Không gian Gia đình (Family Scope)
Một gia đình có thể gồm nhiều thành viên với 3 cấp độ vai trò (Role):
1. **Chủ gia đình (Owner)**:
   - Người tạo nhóm gia đình.
   - Toàn quyền quản trị nhóm: Đổi tên nhóm, tạo mã mời, phê duyệt thành viên, phân quyền vai trò, giải tán nhóm.
   - Toàn quyền quản lý ví gia đình, ngân sách gia đình, giao dịch và quy tắc định kỳ của gia đình.
2. **Biên tập viên (Editor)**:
   - Thành viên tích cực của gia đình.
   - Có quyền: Tạo giao dịch thu/chi trên ví gia đình, chuyển tiền giữa các ví gia đình, tạo và chỉnh sửa ngân sách gia đình, phát sinh giao dịch định kỳ.
   - Không có quyền: Đổi vai trò thành viên khác, xóa nhóm gia đình hoặc xóa các thành viên khác khỏi nhóm.
3. **Người xem (Viewer)**:
   - Thành viên chỉ đọc (Read-only).
   - Có quyền: Xem số dư ví gia đình, xem lịch sử giao dịch gia đình, xem tiến độ ngân sách và báo cáo tài chính chung.
   - Không có quyền: Thêm, sửa, xóa giao dịch hoặc thao tác ngân sách gia đình.

---

## 6. Yêu cầu Hệ thống

### 6.1. Yêu cầu chức năng
- Mọi giao dịch tài chính ghi nhận phải cập nhật số dư ví tức thì theo thời gian thực (không dùng batch job trễ).
- Chuyển tiền bắt buộc phải hạch toán giảm ví nguồn và tăng ví đích trong cùng một database transaction.
- Không được phép ghi đè giao dịch tài chính nếu không có quyền hợp lệ.
- Hỗ trợ xuất dữ liệu ra định dạng chuẩn CSV để mở bằng Excel hoặc phần mềm kế toán.

### 6.2. Yêu cầu phi chức năng
- **Bảo mật**: Mật khẩu được băm bằng Argon2id; Session token được hash SHA-256 trong database; Cookie truyền qua giao thức có cờ `HttpOnly; SameSite=Lax`.
- **Độ tin cậy dữ liệu**: Đảm bảo tính toàn vẹn tham chiếu (Referential Integrity) với 31 Foreign Keys, sử dụng Foreign Key Constraints và Transaction Rollback khi có lỗi.
- **Khả năng quan sát (Observability)**: Tích hợp middleware chuẩn hóa endpoint Health Check Liveness (`/api/v1/health/liveness`) và Readiness (`/api/v1/health/readiness` - kiểm tra kết nối PostgreSQL thực tế).
- **Giao diện & Trải nghiệm (UI/UX)**: Giao diện sáng dịu Fresh Family Finance, responsive trên Desktop, Tablet và Mobile, không bị vỡ bố cục hay tràn thanh cuộn ngang.

---

## 7. Kiến trúc Hệ thống

### 7.1. Kiến trúc tổng thể (3-Tier Architecture)
Hệ thống được thiết kế theo mô hình 3 lớp tách biệt rõ ràng:
1. **Presentation Layer (Frontend)**:
   - React 19 + TypeScript xây dựng Single Page Application (SPA).
   - Vite làm công cụ đóng gói và dev server cục bộ tại cổng `5173`.
   - Quản trị trạng thái người dùng qua `AuthContext` và API client tập trung `apiClient.ts` (Axios với `withCredentials: true`).
2. **Business Logic Layer (Backend API)**:
   - FastAPI (Python) cung cấp RESTful APIs bất đồng bộ và đồng bộ tại cổng `8001`.
   - Pydantic v2 chịu trách nhiệm kiểm tra tính hợp lệ dữ liệu (Data Validation & Serialization).
   - Service Layer tách biệt hoàn toàn giữa Router (tiếp nhận HTTP Request) và Service (xử lý logic nghiệp vụ và truy vấn ORM).
3. **Data Persistence Layer (Database)**:
   - PostgreSQL 18 chạy trong Docker container cô lập tại cổng host `5434`.
   - SQLAlchemy 2.0 ORM quản lý phiên làm việc (`SessionLocal`) và định nghĩa Schema.
   - Alembic quản lý các phiên bản dịch chuyển cấu trúc dữ liệu (Migrations).

---

## 8. Các luồng nghiệp vụ chính

### 8.1. Luồng Xác thực & Quản lý Phiên
```text
[Người dùng] --(POST email, password)--> [API /api/v1/auth/login]
                                                   |
   [Kiểm tra Argon2id Password Hash] <-------------+
                   | (Hợp lệ)
   [Sinh 32-byte Opaque Raw Token]
   [Lưu SHA-256(Raw Token) vào bảng auth_sessions]
   [Gắn Cookie session_id (HttpOnly, SameSite=Lax) vào Response Header]
                   |
[Client lưu cookie tự động, chuyển hướng sang /dashboard]
```

### 8.2. Luồng Chuyển tiền (Transfers) & Bút toán kép
```text
[Người dùng] --(Chuyển tiền: Ví A -> Ví B, số tiền X, phí F)--> [TransferService]
                                                                        |
   [Bắt đầu DB Transaction] <-------------------------------------------+
   [Kiểm tra quyền trên Ví A và Ví B]
   [Kiểm tra cùng loại tiền tệ currency]
   [Tạo bản ghi Transfer: from_account_id=A, to_account_id=B, amount=X, fee_amount=F]
   [Tạo Giao dịch 1: Chi tiền từ Ví A (-X)]
   [Tạo Giao dịch 2: Thu tiền vào Ví B (+X)]
   [Nếu F > 0: Tạo Giao dịch 3: Chi phí chuyển từ Ví A (-F)]
   [Cập nhật số dư Ví A = A - X - F]
   [Cập nhật số dư Ví B = B + X]
   [Commit Transaction]
```

### 8.3. Luồng Giao dịch định kỳ & Chống phát sinh trùng
```text
[Kích hoạt Phát sinh Giao dịch] --> [RecurringTransactionService.generate_due_transaction]
                                                   |
   [Kiểm tra trạng thái quy tắc: Phải là 'active'] |
   [Kiểm tra kỳ hạn: next_due_date <= target_date] |
   [Bắt đầu DB Transaction có khóa FOR UPDATE]     |
   [Kiểm tra bảng transactions: đã có giao dịch gắn recurring_rule_id kỳ này chưa?]
         |                                         |
    (Đã tồn tại)                               (Chưa có)
         |                                         |
   [Bỏ qua, trả về giao dịch cũ]         [Tạo Transaction mới]
                                         [Cập nhật số dư ví tương ứng]
                                         [Tính next_due_date tiếp theo]
                                         [Ghi nhận thông báo phát sinh]
                                         [Commit Transaction]
```

---

## 9. Thiết kế Cơ sở Dữ liệu & Quan hệ Thực thể

Cơ sở dữ liệu gồm đúng **14 bảng** chuẩn hóa và **31 Foreign Keys**:

| STT | Tên bảng | Mục đích | Khóa chính | Khóa ngoại chính |
|---|---|---|---|---|
| 1 | `users` | Tài khoản người dùng | `id` (UUID) | - |
| 2 | `auth_sessions` | Phiên đăng nhập HttpOnly | `id` (UUID) | `user_id` -> `users.id` |
| 3 | `email_verification_tokens` | Token kích hoạt email | `id` (UUID) | `user_id` -> `users.id` |
| 4 | `password_reset_tokens` | Token đặt lại mật khẩu | `id` (UUID) | `user_id` -> `users.id` |
| 5 | `families` | Nhóm không gian gia đình | `id` (UUID) | `owner_id` -> `users.id` |
| 6 | `family_members` | Thành viên gia đình & vai trò | `id` (UUID) | `family_id` -> `families.id`, `user_id` -> `users.id` |
| 7 | `family_invitations` | Lời mời tham gia gia đình | `id` (UUID) | `family_id` -> `families.id`, `invited_by_id` -> `users.id` |
| 8 | `accounts` | Ví tiền tài khoản | `id` (UUID) | `user_id` -> `users.id`, `family_id` -> `families.id` |
| 9 | `categories` | Cây danh mục thu chi | `id` (UUID) | `user_id`, `family_id`, `parent_id` -> `categories.id` |
| 10 | `transactions` | Bản ghi giao dịch thu/chi | `id` (UUID) | `account_id`, `category_id`, `user_id`, `transfer_id`, `recurring_rule_id` |
| 11 | `transfers` | Bản ghi điều chuyển tiền | `id` (UUID) | `from_account_id`, `to_account_id`, `user_id`, `fee_category_id` |
| 12 | `budgets` | Hạn mức ngân sách tháng | `id` (UUID) | `category_id`, `user_id`, `family_id` |
| 13 | `recurring_transactions` | Quy tắc giao dịch lặp | `id` (UUID) | `account_id`, `category_id`, `user_id`, `family_id` |
| 14 | `notifications` | Thông báo hệ thống | `id` (UUID) | `user_id` -> `users.id`, `family_id` -> `families.id` |

---

## 10. Xác thực, Phân quyền & Bảo vệ Dữ liệu

### 10.1. Cơ chế Xác thực Stateful Session (Không dùng Stateless JWT)
- **Lý do lựa chọn**: Đối với ứng dụng quản lý tài chính, khả năng thu hồi quyền truy cập (Instant Revocation) là tối quan trọng. Với JWT stateless, khi người dùng bấm Đăng xuất hoặc nghi ngờ rò rỉ, token cũ vẫn có hiệu lực cho đến khi hết hạn (trừ khi xây dựng blacklist phức tạp trong Redis).
- **Giải pháp**: Hệ thống sinh chuỗi token ngẫu nhiên an toàn bằng `secrets.token_urlsafe(32)`. Client chỉ giữ token qua cookie `HttpOnly`, server chỉ lưu mã băm `SHA-256` của token trong bảng `auth_sessions`. Khi người dùng đăng xuất, server cập nhật `revoked_at` hoặc xóa bản ghi phiên, vô hiệu hóa phiên làm việc ngay lập tức.

### 10.2. Chống tấn công Timing Attack & User Enumeration
- Khi kiểm tra đăng nhập (`authenticate_and_create_session`), nếu email không tồn tại trong database, hệ thống vẫn thực thi hàm `verify_password` với chuỗi hash mẫu (dummy hash) để thời gian phản hồi giữa "email sai" và "mật khẩu sai" là tương đương nhau, ngăn chặn kẻ tấn công dò tìm danh sách email hợp lệ qua độ trễ mạng.

### 10.3. Xóa mềm (Soft-Delete)
- Các thực thể quan trọng (`users`, `accounts`, `categories`, `transactions`, `budgets`) đều cài đặt cột `deleted_at`.
- Khi người dùng xóa một giao dịch, hệ thống không chạy lệnh `DELETE FROM ...` vật lý mà gán `deleted_at = now()`. Điều này giúp giữ nguyên tính toàn vẹn lịch sử sổ sách kế toán và cho phép khôi phục khi cần thiết.

---

## 11. Nguyên tắc Tính toán Số dư, Chuyển tiền & Ngân sách

1. **Số dư ví thực tế**:
   - `Số dư hiện tại = Số dư ban đầu (initial_balance) + Tổng thu (income) - Tổng chi (expense)`.
   - Mỗi khi một giao dịch được thêm, sửa số tiền hoặc xóa mềm, hàm service sẽ cập nhật trường `current_balance` của bảng `accounts` trong cùng một transaction.
2. **Không làm méo mó báo cáo khi Chuyển tiền**:
   - Giao dịch chuyển tiền được đánh dấu loại `transfer`. Khi lập báo cáo thu chi tháng (`ReportsPage`), hệ thống chỉ tổng hợp các giao dịch `type = 'income'` và `type = 'expense'`, loại trừ giao dịch chuyển khoản nội bộ. Do đó dòng tiền thu/chi thực tế không bị tính khống.
3. **Phân tách Đa tiền tệ (Multi-Currency Isolation)**:
   - Hệ thống không cộng gộp số tiền khác loại tiền tệ (ví dụ không cộng trực tiếp 1.000.000 VND với 50 USD thành 1.000.050).
   - Mọi báo cáo số dư, dòng tiền và biểu đồ trên Dashboard đều phân nhóm riêng theo từng loại tiền tệ (`CurrencyBalanceInfo`, `CurrencyCashFlowInfo`).

---

## 12. Giao dịch định kỳ & Cơ chế chống trùng lặp (Idempotency)

- Mỗi quy tắc định kỳ (`RecurringTransaction`) lưu cấu hình chu kỳ (`frequency`: DAILY, WEEKLY, MONTHLY, YEARLY), ngày đến hạn kế tiếp (`next_due_date`) và ngày bắt đầu/kết thúc.
- **Cơ chế chống phát sinh trùng**:
  1. Khi phát sinh giao dịch, bảng `transactions` ghi nhận trường khóa ngoại `recurring_rule_id`.
  2. Bảng `transactions` thiết lập ràng buộc duy nhất (Unique Constraint) hoặc kiểm tra đồng thời kỳ giao dịch trong database transaction có khóa dòng (`with_for_update`).
  3. Nếu người dùng bấm nút "Tạo giao dịch ngay" nhiều lần liên tiếp, hệ thống phát hiện giao dịch của kỳ này đã tồn tại và trả về bản ghi hiện hữu, ngăn chặn trừ tiền ví nhiều lần.

---

## 13. Trung tâm Thông báo (Notifications Center)

- Quản lý các loại thông báo: Cảnh báo ngân sách vượt ngưỡng, nhắc nhở giao dịch định kỳ đến hạn, lời mời gia đình mới, giao dịch chuyển tiền lớn.
- **Cơ chế đồng bộ hiện tại**:
  - Polling định kỳ kết hợp EventBus nội bộ `notification-sync` trên Frontend.
  - Khi có giao dịch phát sinh hoặc người dùng đánh dấu đã đọc, event bus phát tín hiệu làm mới số lượng chưa đọc (`unread_count`) trên chuông thông báo Header ngay lập tức mà không cần tải lại toàn bộ trang.
- **Giới hạn kỹ thuật**: Hiện tại hệ thống hoạt động trên môi trường Web cục bộ, chưa tích hợp máy chủ gửi email thực tế (SMTP) hoặc Push Notification trên thiết bị di động (FCM).

---

## 14. Kiểm thử & Kết quả Xác minh

### 14.1. Bộ kiểm thử tự động Backend (Pytest)
- **Tổng số ca kiểm thử**: **167 tests**.
- **Kết quả thực thi**: **167 passed (100%)**, thời gian chạy ~9.93 giây.
- **Phạm vi kiểm thử**:
  - `test_auth_api.py`, `test_auth_models.py`: Đăng ký, đăng nhập, bảo vệ cookie, timing attack, thu hồi phiên.
  - `test_account_api.py`, `test_account_model.py`: Tạo ví, cập nhật số dư, phân quyền cá nhân/gia đình.
  - `test_transaction_api.py`, `test_transaction_model.py`: CRUD giao dịch, cập nhật số dư tức thì, xóa mềm.
  - `test_transfer_api.py`, `test_transfer_model.py`: Bút toán kép, phí chuyển tiền, void transfer.
  - `test_budget_api.py`, `test_budget_model.py`: Hạn mức ngân sách, tính % tiêu thụ, cảnh báo ngưỡng.
  - `test_family_api.py`, `test_family_models.py`: Tạo nhóm, mã mời, phân quyền Owner/Editor/Viewer.
  - `test_recurring_transaction_api.py`: Tính chu kỳ lặp, phát sinh giao dịch, chống tạo trùng.
  - `test_notification_api.py`: Vòng đời thông báo, đếm chưa đọc, đánh dấu đã đọc, lưu trữ.
  - `test_report_api.py`: Đối sánh dòng tiền, cơ cấu chi tiêu, tính đúng đắn dữ liệu xuất CSV.
  - `test_health.py`: Liveness và Readiness check.

### 14.2. Kiểm tra tĩnh & Linter
- **Backend**: `ruff check backend scripts` -> **All checks passed!**
- **Frontend Build**: `tsc -b && vite build` -> **Hoàn thành thành công (0 errors)**.
- **Frontend Lint**: `npm run lint` -> **0 errors** (37 warnings tiền định của React Compiler về memoization effect).

### 14.3. Kiểm thử kịch bản trực tiếp (Live Verification Scripts)
- `scripts/check_demo.ps1`: Kiểm tra 5/5 tiêu chí hạ tầng (Docker, PostgreSQL 18 cổng 5434, FastAPI cổng 8001, Vite cổng 5173, Alembic Migration `4dc2493f258e`).
- `scripts/verify_live_notification_flow.py`: Xác minh luồng phát sinh giao dịch định kỳ tự động tạo thông báo trên PostgreSQL thật.
- `scripts/verify_e2e_full_acceptance.py`: Chạy kịch bản tích hợp xuyên suốt toàn bộ 10 chức năng trên cơ sở dữ liệu thật.

---

## 15. Hạn chế còn tồn tại
1. **Chưa hỗ trợ tỷ giá chuyển đổi thời gian thực giữa các đồng tiền**: Các ví khác đơn vị tiền tệ hiện chỉ được theo dõi độc lập, chưa có tính năng tự động quy đổi VND sang USD theo tỷ giá ngân hàng hàng ngày.
2. **Chưa tích hợp dịch vụ bên thứ ba**: Chưa tích hợp cổng thanh toán trực tiếp từ ngân hàng (Open Banking / VietQR) hoặc máy chủ gửi email xác thực thực tế (hiện dùng token nội bộ).
3. **Đồng bộ thông báo dựa trên Web Polling**: Chưa áp dụng WebSocket hai chiều hoặc Web Push Notification khi người dùng tắt trình duyệt.

---

## 16. Hướng phát triển tiếp theo
1. Tích hợp quét mã hóa đơn (OCR Invoice Scanning) sử dụng AI để tự động trích xuất số tiền, ngày tháng và danh mục từ ảnh chụp hóa đơn.
2. Xây dựng ứng dụng di động đa nền tảng (React Native / Flutter) tái sử dụng toàn bộ RESTful API backend hiện có.
3. Tích hợp giao thức WebSocket để cập nhật số dư và thông báo thời gian thực ngay khi thành viên khác trong gia đình vừa ghi nhận giao dịch.
4. Cung cấp tính năng gợi ý lập ngân sách thông minh dựa trên lịch sử chi tiêu trung bình 3 tháng gần nhất.

---

## 17. Kết luận
Đồ án **Hệ thống Quản lý Chi tiêu Cá nhân và Gia đình** đã hoàn thành xuất sắc toàn bộ các mục tiêu đặt ra:
- Xây dựng thành công một hệ thống phần mềm hoàn chỉnh, chạy thực tế 100% với kiến trúc 3 lớp rõ ràng và chuẩn mực.
- Đáp ứng nghiêm ngặt các yêu cầu nghiệp vụ tài chính: bảo toàn số dư, bút toán kép, chống tạo trùng giao dịch định kỳ, phân quyền chặt chẽ giữa cá nhân và gia đình.
- Giao diện người dùng Fresh Family Finance hiện đại, sáng dịu, thân thiện và có độ hoàn thiện cao.
- Hệ thống đã được kiểm thử toàn diện với 167 automated tests và các script xác minh trực tiếp trên PostgreSQL 18, hoàn toàn sẵn sàng cho buổi báo cáo và bảo vệ đồ án.

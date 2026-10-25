# BỘ CÂU HỎI PHẢN BIỆN & HƯỚNG DẪN TRẢ LỜI BẢO VỆ ĐỒ ÁN
# HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN VÀ GIA ĐÌNH

---

### Câu 1: Tại sao đồ án lại lựa chọn FastAPI cho Backend thay vì Node.js (Express/NestJS) hay Django?
- **Trả lời**:
  - **Hiệu năng & Tối ưu bất đồng bộ**: FastAPI được xây dựng trên Starlette và Pydantic, hỗ trợ lập trình bất đồng bộ (`async/await`) hiệu năng cao tiệm cận Go và Node.js.
  - **Pydantic v2**: Khả năng kiểm tra tính hợp lệ dữ liệu (validation) tự động, ép kiểu chặt chẽ và sinh OpenAPI docs (Swagger) trực tiếp từ code mà không cần viết tài liệu thủ công.
  - **Nhẹ và linh hoạt hơn Django**: Django quá cồng kềnh với nhiều tính năng thừa (như Django ORM không linh hoạt bằng SQLAlchemy 2.0). FastAPI cho phép kiểm soát hoàn toàn vòng đời kết nối database và kiến trúc phân lớp.

---

### Câu 2: Tại sao Frontend lại sử dụng React kết hợp TypeScript và Vite mà không dùng Create React App (CRA) hay Next.js?
- **Trả lời**:
  - **Vite thay thế CRA**: CRA đã bị Facebook ngừng phát triển; Vite sử dụng Rollup và ES Modules Native, tốc độ khởi động server và Hot Module Replacement (HMR) tính bằng mili-giây, kích thước build tối ưu.
  - **TypeScript**: Giúp phát hiện lỗi cú pháp, kiểu dữ liệu ngay trong quá trình biên dịch (compile-time), đặc biệt quan trọng với các ứng dụng tài chính để tránh lỗi tính toán do nhầm lẫn giữa kiểu chuỗi và kiểu số.
  - **Tại sao không dùng Next.js**: Dự án là một ứng dụng quản trị nội bộ sau đăng nhập (Private Dashboard), không yêu cầu SEO cho trang công khai, do đó kiến trúc Single Page Application (SPA) với React Router là lựa chọn tối ưu, dễ triển khai qua Nginx hoặc Docker mà không cần máy chủ Node.js SSR phức tạp.

---

### Câu 3: Vì sao dự án lựa chọn PostgreSQL mà không phải cơ sở dữ liệu NoSQL như MongoDB?
- **Trả lời**:
  - Dữ liệu tài chính kế toán đòi hỏi tuyệt đối tính toàn vẹn **ACID (Atomicity, Consistency, Isolation, Durability)** và quan hệ ràng buộc chặt chẽ (Referential Integrity).
  - PostgreSQL hỗ trợ kiểm soát khóa ngoại (Foreign Keys), ràng buộc kiểm tra (`CHECK` constraints) và cơ chế khóa dòng giao dịch (`SELECT ... FOR UPDATE`).
  - NoSQL (như MongoDB) không tối ưu cho các phép tính tổng hợp phức tạp (GROUP BY, JOIN nhiều bảng giữa accounts, transactions, categories) và dễ dẫn đến sai lệch số dư khi xảy ra lỗi mạng giữa chừng.

---

### Câu 4: Hãy nêu các bảng dữ liệu chính trong hệ thống và mối quan hệ giữa chúng?
- **Trả lời**:
  - Hệ thống gồm **14 bảng** chuẩn hóa và **31 Foreign Keys**:
    1. `users`: Bảng trung tâm lưu tài khoản người dùng.
    2. `auth_sessions`: Lưu phiên đăng nhập an toàn (liên kết 1-N với `users`).
    3. `families` và `family_members`: Quản lý nhóm gia đình và phân quyền thành viên (quan hệ N-N giữa `users` và `families`).
    4. `accounts`: Lưu ví tiền (thuộc sở hữu của `user_id` cá nhân hoặc `family_id` gia đình).
    5. `categories`: Danh mục thu chi phân cấp cha - con (`parent_id` trỏ về chính nó).
    6. `transactions`: Lưu từng bút toán thu/chi (liên kết với `accounts`, `categories`, `transfers`, `recurring_transactions`).
    7. `transfers`: Lưu lệnh điều chuyển tiền giữa hai ví (`from_account_id` và `to_account_id`).
    8. `budgets`: Lưu định mức chi tiêu theo tháng và danh mục.
    9. `recurring_transactions`: Lưu quy tắc phát sinh định kỳ.
    10. `notifications`: Lưu thông báo hệ thống.

---

### Câu 5: Hệ thống sử dụng cơ chế xác thực nào? Tại sao không dùng Stateless JWT Token lưu trong LocalStorage?
- **Trả lời**:
  - **Cơ chế thực tế**: Dự án sử dụng **Stateful Opaque Session Token** lưu trong cơ sở dữ liệu và truyền qua **HttpOnly Cookie**.
  - **Lý do không dùng Stateless JWT trong LocalStorage**:
    1. **Nguy cơ XSS**: Nếu token lưu trong `localStorage`, bất kỳ đoạn mã JavaScript độc hại nào chạy trên trình duyệt đều có thể đánh cắp token. Cookie `HttpOnly` ngăn chặn hoàn toàn JavaScript truy cập.
    2. **Khả năng thu hồi tức thì (Instant Revocation)**: Với JWT thuần túy (stateless), khi người dùng bấm Đăng xuất hoặc khi tài khoản bị khóa, token vẫn hợp lệ cho đến khi hết hạn. Với Session trong PostgreSQL, khi bấm Đăng xuất, server cập nhật trạng thái thu hồi trong bảng `auth_sessions`, phiên làm việc bị hủy ngay lập tức trên mọi yêu cầu kế tiếp.

---

### Câu 6: Làm thế nào server bảo vệ Session Token trong cơ sở dữ liệu nếu database bị rò rỉ (dump database)?
- **Trả lời**:
  - Server **không bao giờ lưu raw token** trong cơ sở dữ liệu.
  - Khi người dùng đăng nhập thành công:
    - Server sinh chuỗi ngẫu nhiên 32-byte an toàn: `raw_token = secrets.token_urlsafe(32)`.
    - Server tính mã băm một chiều: `token_hash = hashlib.sha256(raw_token.encode()).hexdigest()`.
    - Chỉ lưu `token_hash` vào cột `token_hash` trong bảng `auth_sessions`.
    - Trả `raw_token` về cho client qua cookie.
  - Nếu kẻ tấn công đánh cắp được database, chúng chỉ có chuỗi hash SHA-256 và không thể dùng chuỗi này để giả mạo phiên gửi lên server.

---

### Câu 7: Thuật toán mã hóa mật khẩu đang sử dụng là gì và tại sao lại chọn nó?
- **Trả lời**:
  - Dự án sử dụng thuật toán **Argon2id** (thông qua thư viện `argon2-cffi`), là thuật toán chiến thắng tại cuộc thi Password Hashing Competition (PHC) quốc tế.
  - **Ưu điểm**: Argon2id kết hợp cả chống tấn công bằng bộ nhớ (memory-hard) và chống tấn công bằng thời gian (time-hard), có khả năng chống lại các cuộc tấn công bẻ khóa bằng chip chuyên dụng GPU/ASIC vượt trội hơn hẳn so với MD5, SHA-256 truyền thống, và an toàn hơn Bcrypt.

---

### Câu 8: Hệ thống phòng chống Timing Attack và User Enumeration trong quá trình đăng nhập như thế nào?
- **Trả lời** (Theo code tại `AuthService.authenticate_and_create_session`):
  - **Chống User Enumeration**: Hệ thống trả về thông báo lỗi chung `"Email hoặc mật khẩu không chính xác"` cho cả hai trường hợp email không tồn tại hoặc mật khẩu sai.
  - **Chống Timing Attack**: Nếu email không tồn tại trong hệ thống, server vẫn cố tình thực thi hàm `verify_password` với một chuỗi hash giả định (`dummyhash`) để thời gian xử lý CPU cho request đó tương đương với request có email tồn tại nhưng sai mật khẩu, khiến kẻ tấn công không thể đo thời gian phản hồi mạng để suy đoán email người dùng.

---

### Câu 9: Cơ chế kiểm soát quyền truy cập dữ liệu giữa Cá nhân và Gia đình được cài đặt ra sao?
- **Trả lời**:
  - Mỗi thực thể tài chính (`accounts`, `categories`, `transactions`, `budgets`) đều có trường `scope` mang giá trị `'personal'` hoặc `'family'`.
  - **Ví cá nhân**: Endpoint kiểm tra điều kiện nghiêm ngặt: `account.user_id == current_user.id` và `account.scope == 'personal'`. Người dùng khác tuyệt đối không truy vấn được.
  - **Ví gia đình**: Endpoint kiểm tra quyền thành viên trong bảng `family_members`: Người dùng phải có bản ghi liên kết `user_id == current_user.id` và `family_id == account.family_id`. Nếu không phải thành viên, server lập tức trả mã lỗi `403 Forbidden`.

---

### Câu 10: Ba vai trò Owner, Editor và Viewer trong Gia đình khác nhau như thế nào?
- **Trả lời**:
  - **Chủ nhóm (Owner)**: Toàn quyền quản trị nhóm gia đình, đổi tên nhóm, tạo mã mời thành viên, phân quyền hoặc hạ quyền thành viên khác, và có thể xóa nhóm.
  - **Biên tập viên (Editor)**: Được phép tạo giao dịch thu chi, chuyển tiền giữa các ví gia đình, thiết lập ngân sách gia đình và phát sinh giao dịch định kỳ; không thể chỉnh sửa vai trò của thành viên khác hoặc xóa nhóm.
  - **Người xem (Viewer)**: Chỉ được cấp quyền đọc (Read-only); có thể xem số dư ví, danh sách giao dịch, tiến độ ngân sách và báo cáo; mọi thao tác thêm/sửa/xóa đều bị từ chối với mã lỗi `403 Forbidden`.

---

### Câu 11: Số dư ví tài khoản được tính toán như thế nào và làm sao đảm bảo không bị sai lệch?
- **Trả lời**:
  - Số dư hiện tại được lưu ở trường `current_balance` trong bảng `accounts`.
  - `Số dư = initial_balance + Tổng thu nhập hợp lệ - Tổng chi tiêu hợp lệ`.
  - **Đảm bảo tính chính xác**: Bất kỳ thao tác thêm mới giao dịch, chỉnh sửa số tiền, xóa mềm hay hủy giao dịch chuyển tiền đều cập nhật trường `current_balance` trong cùng một database transaction. Nếu có lỗi xảy ra ở bất kỳ bước nào, toàn bộ transaction được `rollback`, số dư không bao giờ bị cập nhật nửa vời.

---

### Câu 12: Tại sao Chuyển tiền (Transfers) lại áp dụng nguyên tắc bút toán kép (Double-Entry)?
- **Trả lời**:
  - Nếu chuyển tiền chỉ đơn thuần trừ tiền ví A và cộng tiền ví B mà không có cơ chế quản lý giao dịch kép, khi lập báo cáo tài chính cuối tháng, hệ thống sẽ nhầm lẫn ví A "chi tiêu" và ví B "thu nhập", làm sai lệch chỉ số chi tiêu và thu nhập thực tế của người dùng.
  - Với nguyên tắc bút toán kép, hệ thống tạo bản ghi `Transfer` và gắn cờ loại giao dịch là `transfer`. Báo cáo tài chính thu chi loại bỏ loại giao dịch này ra khỏi doanh thu và chi phí, đảm bảo bản chất dòng tiền chỉ là luân chuyển tài sản giữa các ví.

---

### Câu 13: Xử lý phí chuyển tiền (Transfer Fee) và chức năng Hủy lệnh chuyển (Void Transfer) diễn ra như thế nào?
- **Trả lời**:
  - **Phí chuyển tiền**: Khi chuyển tiền có phí (ví dụ chuyển 500k, phí 5k):
    - Ví nguồn bị trừ: `500.000 + 5.000 = 505.000 ₫`.
    - Ví đích được cộng: `500.000 ₫`.
    - Khoản phí 5.000 ₫ được tách thành một giao dịch chi tiêu riêng loại `expense` gắn với danh mục phí dịch vụ ngân hàng, giúp phản ánh đúng khoản hao hụt thực tế.
  - **Hủy lệnh chuyển (Void Transfer)**:
    - Khi người dùng bấm Hủy (Void), hệ thống đánh dấu `is_voided = True` trên bản ghi transfer.
    - Tự động hoàn trả số tiền gốc và phí về ví nguồn, đồng thời khấu trừ tiền từ ví đích trong cùng một transaction.

---

### Câu 14: Soft-delete (Xóa mềm) là gì và vì sao lại áp dụng cho dự án tài chính thay vì Xóa cứng (Hard-delete)?
- **Trả lời**:
  - **Khái niệm**: Xóa mềm là việc đánh dấu thời gian xóa vào cột `deleted_at` (`deleted_at = now()`) thay vì xóa bản ghi khỏi database bằng câu lệnh `DELETE`. Mọi câu lệnh truy vấn thông thường sẽ lọc thêm điều kiện `WHERE deleted_at IS NULL`.
  - **Tầm quan trọng trong tài chính**:
    1. **Bảo toàn lịch sử sổ sách kế toán**: Không làm đứt gãy tính toàn vẹn tham chiếu với các bảng báo cáo, ngân sách và lịch sử kiểm toán.
    2. **Khôi phục dữ liệu**: Cho phép người dùng hoặc quản trị viên hoàn tác khi lỡ tay xóa nhầm giao dịch quan trọng.

---

### Câu 15: Tiến độ chi tiêu theo Ngân sách (Budgets) được tính toán như thế nào?
- **Trả lời**:
  - Khi người dùng thiết lập ngân sách cho một danh mục trong tháng (ví dụ: Danh mục Ăn uống, Hạn mức 5.000.000 ₫ cho tháng 05/2026):
  - Server thực hiện truy vấn tổng tiền chi tiêu thực tế:
    ```sql
    SELECT SUM(amount) FROM transactions
    WHERE category_id = :cat_id
      AND type = 'expense'
      AND occurred_at BETWEEN :start_of_month AND :end_of_month
      AND deleted_at IS NULL
    ```
  - `Tỷ lệ chi tiêu = (Tổng tiền đã chi / Hạn mức) * 100%`.
  - Dựa trên tỷ lệ này, hệ thống gắn nhãn trạng thái:
    - Nhỏ hơn ngưỡng cảnh báo (80%): `An toàn` (Xanh).
    - Từ 80% đến 100%: `Cảnh báo tiệm cận` (Vàng hổ phách).
    - Lớn hơn 100%: `Vượt hạn mức` (Đỏ).

---

### Câu 16: Làm thế nào hệ thống tránh cộng gộp sai lệch giữa các loại tiền tệ khác nhau (VND, USD)?
- **Trả lời**:
  - Hệ thống áp dụng nguyên tắc **Multi-Currency Isolation**:
  - Mọi bản ghi ví (`accounts`), giao dịch (`transactions`), ngân sách (`budgets`) đều lưu mã tiền tệ ISO 3 chữ cái (ví dụ `VND`, `USD`).
  - Khi tổng hợp dữ liệu trên Dashboard và Báo cáo, hệ thống thực hiện `GROUP BY currency`, trả về danh sách các khối độc lập:
    - Số dư VND riêng.
    - Số dư USD riêng.
  - Tuyệt đối không có phép cộng gộp số học thô giữa 1.000.000 VND và 50 USD, tránh làm biến dạng số liệu tài chính.

---

### Câu 17: Giao dịch định kỳ (Recurring Transactions) hoạt động như thế nào và cơ chế chống phát sinh trùng lặp (Idempotency) là gì?
- **Trả lời**:
  - Mỗi quy tắc định kỳ lưu cấu hình: chu kỳ (`frequency`: DAILY, WEEKLY, MONTHLY, YEARLY), ngày đến hạn kế tiếp (`next_due_date`).
  - Khi đến hạn, hệ thống tính toán và cho phép phát sinh giao dịch.
  - **Chống phát sinh trùng lặp**:
    1. Trong hàm `generate_due_transaction`, server mở transaction và khóa dòng bản ghi quy tắc bằng `with_for_update()`.
    2. Server kiểm tra xem đã có giao dịch nào trong bảng `transactions` có `recurring_rule_id = rule.id` cho kỳ thanh toán này hay chưa.
    3. Nếu đã tồn tại, hàm trả về giao dịch cũ mà không tạo thêm giao dịch mới.
    4. Chỉ khi chưa có, server mới tạo bản ghi giao dịch mới, cập nhật số dư ví và cộng thêm thời gian vào `next_due_date` cho kỳ tiếp theo.

---

### Câu 18: Công cụ Alembic đóng vai trò gì trong dự án?
- **Trả lời**:
  - Alembic là công cụ quản lý các phiên bản dịch chuyển cấu trúc cơ sở dữ liệu (Database Migration tool) cho SQLAlchemy.
  - **Tác dụng**:
    1. Lưu vết lịch sử thay đổi cấu trúc bảng (thêm cột, sửa kiểu dữ liệu, thêm index, foreign key) dưới dạng các file mã nguồn Python có thể kiểm soát phiên bản qua Git.
    2. Cho phép tự động cập nhật schema database (`alembic upgrade head`) hoặc hạ cấp schema (`alembic downgrade -1`) đồng nhất giữa môi trường phát triển của lập trình viên và môi trường production/docker mà không làm mất dữ liệu hiện hữu.

---

### Câu 19: Tại sao dự án chưa tích hợp gửi Email thực tế hoặc Push Notification qua điện thoại?
- **Trả lời**:
  - Trong phạm vi của đồ án tốt nghiệp, mục tiêu cốt lõi là tập trung hoàn thiện 100% nghiệp vụ tài chính, tính đúng đắn của sổ sách kế toán, kiến trúc bảo mật session và trải nghiệm giao diện người dùng trên môi trường web cục bộ (Local Lab / Docker Compose).
  - Việc tích hợp Email (SMTP bên thứ ba như SendGrid/Gmail) hoặc Push Notification (Firebase Cloud Messaging - FCM) đòi hỏi tên miền công khai (public domain), cấu hình DNS (SPF, DKIM) và chứng chỉ dịch vụ trả phí. Do đó, hệ thống tập trung hoàn thiện Trung tâm thông báo In-App Notification Center hoạt động độc lập và ổn định mà không bị phụ thuộc vào kết nối Internet bên ngoài.

---

### Câu 20: Những hạn chế lớn nhất hiện tại của hệ thống là gì và hướng nâng cấp tiếp theo?
- **Trả lời**:
  - **Hạn chế hiện tại**:
    1. Chưa có tính năng quét hóa đơn tự động (OCR).
    2. Chưa có biểu đồ quy đổi tỷ giá thời gian thực giữa các ngoại tệ.
    3. Đồng bộ thông báo trên web vẫn đang dùng Web Polling thay vì kênh WebSocket hai chiều.
  - **Hướng nâng cấp**:
    1. Tích hợp mô hình AI trích xuất thông tin hóa đơn (OCR Invoice Parser).
    2. Xây dựng ứng dụng di động đa nền tảng bằng React Native kết nối tới hệ thống FastAPI Backend hiện có.
    3. Triển khai WebSocket để đẩy số dư và thông báo thời gian thực ngay khi có giao dịch phát sinh từ thành viên gia đình khác.

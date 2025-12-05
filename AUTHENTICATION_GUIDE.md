# Tóm tắt các thay đổi cho hệ thống đăng nhập/đăng kí

## 📝 Các file đã thêm/sửa đổi:

### 1. **controller/auth.py** (TẠO MỚI)
File này chứa các hàm xử lý xác thực:
- `register_user(username, password, email)`: Tạo user mới, lưu password không mã hóa
- `login_user(username, password)`: Kiểm tra username/password, trả về user_id nếu đúng
- `get_user_by_id(user_id)`: Lấy thông tin user

### 2. **app.py** (SỬA ĐỔI)
Thêm các import:
- `from flask import session, redirect, url_for`
- `from functools import wraps`
- `from controller.auth import ...`

Thêm các route mới:
- `POST /login`: Xử lý đăng nhập
- `GET /login`: Trả về trang login.html
- `POST /register`: Xử lý đăng kí
- `GET /register`: Trả về trang login.html
- `POST /logout`: Xóa session, đăng xuất
- `GET /api/current-user`: Lấy thông tin user đang đăng nhập

Thêm decorator `@require_login` để bảo vệ route `GET /`

### 3. **templates/login.html** (TẠO MỚI)
Trang đăng nhập/đăng kí với:
- Tab chuyển đổi giữa login và register
- Form đăng nhập: username, password
- Form đăng kí: username, email, password, password confirm
- JavaScript xử lý validation và gửi request đến server
- Hỗ trợ phím Enter để submit form

### 4. **templates/index.html** (SỬA ĐỔI)
Thêm:
- Header với thông tin user và nút logout
- Hàm `loadCurrentUser()`: Lấy thông tin user từ server
- Hàm `handleLogout()`: Xử lý logout
- Cập nhật `onload` để gọi `loadCurrentUser()`

## 🔐 Cách hoạt động:

### Đăng nhập:
1. User nhập username/password vào form
2. JavaScript gửi POST request đến `/login`
3. Backend kiểm tra username/password với database
4. Nếu đúng: lưu user_id vào session, trả về JSON thành công
5. Frontend redirect đến `/` (trang chính)

### Đăng kí:
1. User nhập username/password/confirm vào form
2. JavaScript validate cơ bản (độ dài, trùng password)
3. Gửi POST request đến `/register`
4. Backend kiểm tra username chưa tồn tại
5. Thêm user mới vào database (password không mã hóa)
6. Tự động đăng nhập và redirect đến `/`

### Bảo vệ trang:
- Route `/` dùng decorator `@require_login`
- Nếu chưa đăng nhập (session không có user_id), redirect về `/login`
- Route `/api/current-user` kiểm tra session để lấy thông tin user
- Nút logout gọi `POST /logout` để xóa session

## 📋 Yêu cầu:
- Database có bảng `users` với cột: user_id, username, password, email, role
- Mật khẩu được lưu dạng text (không mã hóa)
- Session được lưu trên server (Flask default)

## ✅ Test đơn giản:
1. Chạy `python app.py`
2. Truy cập http://localhost:5000/login
3. Đăng kí: username="test123", password="123456"
4. Đăng nhập: test123/123456
5. Xem trang chính với tên user trên header
6. Nhấn "Đăng Xuất" để logout

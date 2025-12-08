# Smart Light – Hệ thống điều khiển đèn thông minh

Hệ thống gồm **backend Flask + Socket.IO + MQTT**, CSDL PostgreSQL và firmware ESP32. Cho phép đăng nhập, điều khiển thủ công/tự động, hẹn giờ, cập nhật trạng thái realtime, tích hợp cảm biến chuyển động và theo dõi trạng thái thiết bị.

## 1. Cấu trúc thư mục
```
Source code/
├── backend/
│   ├── app.py                        # Flask entrypoint, routes web/API, init MQTT/Socket.IO, offline checker, start scheduler thread
│   ├── config/
│   │   ├── db.py                     # Kết nối PostgreSQL (chỉnh DB_CONFIG)
│   │   ├── mqtt.py                   # Tạo MQTT client (HiveMQ public/Cloud)
│   │   └── web_socket.py             # Khởi tạo Socket.IO server dùng chung
│   ├── controller/
│   │   ├── auth.py                   # Đăng ký/đăng nhập/lấy user (mật khẩu đang plain text)
│   │   ├── user_controller.py        # Xử lý login/register/logout/current-user, decorator require_login
│   │   ├── devices.py                # MQTT callback, cập nhật DB, publish command, Socket.IO brightness, lấy danh sách devices
│   │   └── scheduler.py              # CRUD lịch, thread schedule_executor gửi lệnh bật/tắt theo giờ
│   ├── templates/
│   │   ├── login.html                # UI đăng nhập/đăng ký
│   │   ├── dashboard.html            # Trang thống kê + danh sách thiết bị, điều hướng điều khiển
│   │   └── index.html                # Trang điều khiển chi tiết 1 thiết bị, chỉnh độ sáng, đặt lịch, realtime
│   └── requirements.txt              # Thư viện Python
├── database/
│   └── schema.sql                    # Schema PostgreSQL (users, devices, schedules, logs) + dữ liệu mẫu
└── firware/
    └── esp32_smart_light/
        └── esp32_smart_light.ino     # Firmware ESP32 điều khiển 2 đèn, MQTT, PIR auto, heartbeat

AUTHENTICATION_GUIDE.md               # Ghi chú thay đổi mô-đun đăng nhập
Documents/                            # Báo cáo PDF
```

## 2. Kiến trúc & thành phần
- Backend Flask + Socket.IO phục vụ web UI, API, và phát realtime tới trình duyệt.
- MQTT broker (mặc định HiveMQ public) chuyển lệnh điều khiển và nhận trạng thái từ ESP32.
- PostgreSQL lưu người dùng, thiết bị, lịch hẹn giờ, log.
- Firmware ESP32 nhận lệnh MQTT, điều khiển 2 đèn, chế độ auto qua PIR, gửi heartbeat/state.

## 3. Tính năng chính
- Đăng nhập/đăng ký (session-based).
- Dashboard: liệt kê thiết bị, thống kê tổng/on/off, điều hướng điều khiển chi tiết.
- Điều khiển thiết bị: ON/OFF, manual/auto, chỉnh độ sáng realtime (Socket.IO), nhận trạng thái MQTT.
- Hẹn giờ bật/tắt: lưu DB, thread scheduler gửi lệnh MQTT, emit `schedule_executed`.
- Giám sát offline: thread kiểm tra `last_online`, đánh dấu offline và emit cập nhật.
- Firmware ESP32: 2 đèn, chế độ auto qua PIR, heartbeat, publish state, nhận lệnh.

## 4. Luồng hoạt động
1) ESP32 kết nối Wi-Fi, subscribe `home/<user>/<device>/cmd`, publish state + heartbeat.
2) Backend subscribe MQTT state, cập nhật DB, emit Socket.IO `device_state_update`.
3) Người dùng đăng nhập → dashboard → chọn `/control/<device_id>` để điều khiển.
4) Lệnh ON/OFF/mode/brightness gửi REST `/api/device/command` hoặc Socket.IO (brightness) → backend publish MQTT `.../cmd` → ESP32 thực thi và publish state.
5) Scheduler đọc bảng `schedules`, đến giờ publish lệnh và emit `schedule_executed`.
6) `offline_checker` đánh dấu offline nếu quá hạn heartbeat và emit cập nhật.

## 5. Cài đặt & chạy nhanh
### Yêu cầu
- Python 3.10+, PostgreSQL 14+, MQTT broker (mặc định HiveMQ public), ESP32.

### Thiết lập
```bash
cd "Source code/backend"
python -m venv .venv && .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```
1) Cấu hình DB: chỉnh `config/db.py` (DB_CONFIG).  
2) Khởi tạo DB: chạy `Source code/database/schema.sql` trên PostgreSQL (tạo bảng + dữ liệu mẫu).  
3) MQTT: nếu dùng broker riêng, sửa `config/mqtt.py` và topic trong firmware (user/device id).  
4) Chạy server:
```bash
python app.py   # lắng nghe 0.0.0.0:5000
```
5) Đăng nhập thử: `admin/admin123` (mật khẩu đang lưu plain text).  
6) Firmware: mở `.ino`, sửa SSID/PASSWORD, MQTT broker, user/device id; biên dịch và nạp ESP32.

## 6. API & giao diện
- Web:
  - `GET /login` – trang đăng nhập/đăng ký.
  - `GET /` – dashboard (cần login).
  - `GET /control/<device_id>` – điều khiển chi tiết.
- Auth API: `POST /login`, `POST /register`, `POST /logout`, `GET /api/current-user`.
- Thiết bị API:
  - `GET /api/devices` – danh sách thiết bị.
  - `POST /api/device/command` – gửi lệnh `{user_id, device_id, state?, mode?, brightness?}`.
- Lịch:
  - `GET /api/schedule/<device_id>` – lấy lịch.
  - `POST /api/schedule/<device_id>` – lưu `{start_time, end_time}`.
- Realtime: Socket.IO event `device_state_update`, `schedule_executed`; client emit `brightness_change`.


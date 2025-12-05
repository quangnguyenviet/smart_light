from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
from functools import wraps

from config.web_socket import socketio
from config.mqtt import create_mqtt_client
from controller.devices import on_message, process_device_command
# THÊM: import các hàm xử lý đăng nhập/đăng kí từ controller auth
from controller.auth import register_user, login_user, get_user_by_id

app = Flask(__name__)
# THÊM: đặt secret key cho session (để lưu user_id)
app.secret_key = 'smart_light_secret_key_2025'
CORS(app)

# init socketio
socketio.init_app(app)

# init mqtt
mqtt_client = create_mqtt_client(on_message)
mqtt_client.subscribe("home/+/+/state")
mqtt_client.loop_start()

# ==================== THÊM: HÀM HELPER KIỂM TRA LOGIN ====================
def require_login(f):
    """
    # Decorator để kiểm tra user đã đăng nhập chưa
    # Nếu chưa, redirect về trang login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # KIỂM TRA: xem session có user_id không
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== THÊM: ROUTE ĐĂNG NHẬP ====================
@app.route("/login", methods=["GET", "POST"])
def login_page():
    """
    # GET: Trả về trang login.html
    # POST: Xử lý form đăng nhập
    """
    if request.method == "GET":
        # THÊM: Trả về trang login
        return render_template("login.html")
    
    # THÊM: Xử lý POST - lấy username và password từ form
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    # THÊM: Validation đơn giản
    if not username or not password:
        return jsonify({"error": "Vui lòng nhập tên đăng nhập và mật khẩu"}), 400
    
    # THÊM: Gọi hàm login_user từ auth controller
    user_id, error = login_user(username, password)
    
    if error:
        # THÊM: Trả về lỗi nếu đăng nhập sai
        return jsonify({"error": error}), 401
    
    # THÊM: Lưu user_id vào session
    session['user_id'] = user_id
    user = get_user_by_id(user_id)
    
    return jsonify({
        "message": "Đăng nhập thành công",
        "user": user
    }), 200

# ==================== THÊM: ROUTE ĐĂNG KÍ ====================
@app.route("/register", methods=["GET", "POST"])
def register_page():
    """
    # GET: Trả về trang đăng kí
    # POST: Xử lý form đăng kí
    """
    if request.method == "GET":
        # THÊM: Trả về trang login.html (chung trang login và register)
        return render_template("login.html")
    
    # THÊM: Xử lý POST - lấy dữ liệu từ form đăng kí
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    password_confirm = data.get("password_confirm", "").strip()
    email = data.get("email", "").strip() or None
    
    # THÊM: Validation đơn giản
    if not username or not password:
        return jsonify({"error": "Vui lòng nhập tên đăng nhập và mật khẩu"}), 400
    
    if len(username) < 3:
        return jsonify({"error": "Tên đăng nhập phải ít nhất 3 ký tự"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Mật khẩu phải ít nhất 6 ký tự"}), 400
    
    # THÊM: Kiểm tra xác nhận mật khẩu
    if password != password_confirm:
        return jsonify({"error": "Mật khẩu xác nhận không trùng"}), 400
    
    # THÊM: Gọi hàm register_user từ auth controller
    user_id, error = register_user(username, password, email)
    
    if error:
        # THÊM: Trả về lỗi nếu đăng kí thất bại
        return jsonify({"error": error}), 400
    
    # THÊM: Tự động đăng nhập sau khi đăng kí thành công
    session['user_id'] = user_id
    user = get_user_by_id(user_id)
    
    return jsonify({
        "message": "Đăng kí thành công",
        "user": user
    }), 201

# ==================== THÊM: ROUTE LOGOUT ====================
@app.route("/logout", methods=["POST"])
def logout():
    """
    # Xóa session user_id để đăng xuất
    """
    # THÊM: Xóa user_id từ session
    session.pop('user_id', None)
    return jsonify({"message": "Đã đăng xuất"}), 200

# ==================== THÊM: ROUTE LẤY THÔNG TIN USER ĐANG ĐĂNG NHẬP ====================
@app.route("/api/current-user", methods=["GET"])
def current_user():
    """
    # Trả về thông tin user đang đăng nhập
    """
    # THÊM: Kiểm tra session có user_id không
    if 'user_id' not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
    
    # THÊM: Lấy thông tin user từ database
    user = get_user_by_id(session['user_id'])
    
    if not user:
        # THÊM: Xóa session nếu user không tồn tại
        session.pop('user_id', None)
        return jsonify({"error": "User không tồn tại"}), 404
    
    return jsonify(user), 200

@app.route("/")
# THÊM: Decorator require_login để kiểm tra đã đăng nhập chưa
@require_login
def home():
    # THÊM: Chỉ user đã đăng nhập mới truy cập được
    return render_template("index.html")

@app.route("/api/device/command", methods=["POST"])
def device_command():
    data = request.json
    response, status = process_device_command(mqtt_client, data)
    return jsonify(response), status

if __name__ == "__main__":
    print("Server running...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

from flask import jsonify, request, session, redirect, url_for, render_template
from functools import wraps
from controller.auth import register_user, login_user, get_user_by_id

# ==================== CHECK LOGIN ====================
def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== LOGIN HANDLER ====================
def handle_login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Vui lòng nhập tên đăng nhập và mật khẩu"}), 400

    user_id, error = login_user(username, password)
    if error:
        return jsonify({"error": error}), 401

    session["user_id"] = user_id
    return jsonify({
        "message": "Đăng nhập thành công",
        "user": get_user_by_id(user_id)
    }), 200


# ==================== REGISTER HANDLER ====================
def handle_register():
    if request.method == "GET":
        return render_template("login.html")

    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    password_confirm = data.get("password_confirm", "").strip()
    email = data.get("email", "").strip() or None

    if not username or not password:
        return jsonify({"error": "Vui lòng nhập tên đăng nhập và mật khẩu"}), 400

    if len(username) < 3:
        return jsonify({"error": "Tên đăng nhập phải ít nhất 3 ký tự"}), 400

    if len(password) < 6:
        return jsonify({"error": "Mật khẩu phải ít nhất 6 ký tự"}), 400

    if password != password_confirm:
        return jsonify({"error": "Mật khẩu xác nhận không trùng"}), 400

    user_id, error = register_user(username, password, email)
    if error:
        return jsonify({"error": error}), 400

    session["user_id"] = user_id
    return jsonify({
        "message": "Đăng kí thành công",
        "user": get_user_by_id(user_id)
    }), 201


# ==================== LOGOUT HANDLER ====================
def handle_logout():
    session.pop("user_id", None)
    return jsonify({"message": "Đã đăng xuất"}), 200


# ==================== CURRENT USER ====================
def handle_current_user():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    user = get_user_by_id(session["user_id"])
    if not user:
        session.pop("user_id", None)
        return jsonify({"error": "User không tồn tại"}), 404

    return jsonify(user), 200

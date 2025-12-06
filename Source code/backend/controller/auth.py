# controller/auth.py
# Module đơn giản để xử lý đăng nhập và đăng kí (không mã hóa mật khẩu)
from config.db import get_db_connection

# ==================== ĐĂNG KÍ ====================
def register_user(username, password, email=None):
    """
    # Tạo tài khoản người dùng mới
    # Lưu mật khẩu dưới dạng text thường (không mã hóa)
    # Trả về: (user_id, error_message)
    """
    conn = None
    try:
        # Kiểm tra username đã tồn tại
        conn = get_db_connection()
        if conn is None:
            return None, "Lỗi kết nối database"
        
        cursor = conn.cursor()
        # Truy vấn kiểm tra username có tồn tại chưa
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone() is not None:
            return None, "Tên đăng nhập đã tồn tại"
        
        # Thêm user mới vào database
        # INSERT user với username, password (text), email, role mặc định là 'user'
        query = """
            INSERT INTO users (username, password, email, role)
            VALUES (%s, %s, %s, 'user')
            RETURNING user_id
        """
        cursor.execute(query, (username, password, email))
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ Đăng kí thành công: {username}")
        return user_id, None
    except Exception as e:
        print(f"❌ Lỗi đăng kí: {e}")
        if conn:
            conn.rollback()
        return None, f"Lỗi: {str(e)}"
    finally:
        if conn:
            conn.close()

# ==================== ĐĂNG NHẬP ====================
def login_user(username, password):
    """
    # Xác thực đăng nhập: kiểm tra username và password trong database
    # So sánh password text với text trong DB (không mã hóa)
    # Trả về: (user_id, error_message)
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return None, "Lỗi kết nối database"
        
        cursor = conn.cursor()
        # Lấy user_id và password từ database với username
        cursor.execute(
            "SELECT user_id, password FROM users WHERE username = %s",
            (username,)
        )
        result = cursor.fetchone()
        
        if result is None:
            # Không tìm thấy user
            return None, "Tên đăng nhập hoặc mật khẩu không đúng"
        
        user_id, db_password = result
        
        # So sánh password nhập vào với password trong DB (text so sánh text)
        if password != db_password:
            # Mật khẩu sai
            return None, "Tên đăng nhập hoặc mật khẩu không đúng"
        
        print(f"✅ Đăng nhập thành công: {username}")
        return user_id, None
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {e}")
        return None, f"Lỗi: {str(e)}"
    finally:
        if conn:
            conn.close()

# ==================== LẤY THÔNG TIN USER ====================
def get_user_by_id(user_id):
    """
    # Lấy thông tin user từ user_id
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor()
        # Lấy username, email, role từ user_id
        cursor.execute(
            "SELECT user_id, username, email, role FROM users WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            return {
                "user_id": result[0],
                "username": result[1],
                "email": result[2],
                "role": result[3]
            }
        return None
    except Exception as e:
        print(f"❌ Lỗi lấy user: {e}")
        return None
    finally:
        if conn:
            conn.close()

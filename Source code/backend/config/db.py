import psycopg2
from datetime import datetime

# ============================
# CẤU HÌNH DATABASE POSTGRES
# ============================
DB_CONFIG = {
    "dbname": "smart_light_db",      # Tên database của bạn
    "user": "postgres",      # Username mặc định
    "password": "123",       # Password của bạn
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    """Tạo kết nối đến PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        # In lỗi kết nối ra console
        print(f"Error connecting to DB: {e}") 
        return None
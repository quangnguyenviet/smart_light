# config/db.py
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "dbname": "smart_light_db",
    "user": "postgres",
    "password": "duong2k4",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Error connecting to DB: {e}")
        return None

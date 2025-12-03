import json
import psycopg2
from datetime import datetime
from config.db import get_db_connection
from config.mqtt import get_mqtt_client

# ===================================================
# HÀM LOGIC XỬ LÝ DATABASE (CRUD)
# ===================================================

def update_device_state(data):
    """Cập nhật trạng thái thiết bị vào PostgreSQL từ MQTT payload"""
    
    device_name = data.get("device_id")
    state = data.get("state") # "on" hoặc "off"
    mode = data.get("mode")
    brightness = data.get("brightness")
    
    is_on = (state == "on")
    now = datetime.now() 

    conn = None
    try:
        conn = get_db_connection()
        if conn is None: return

        cursor = conn.cursor()
        
        update_query = """
        UPDATE devices
        SET 
            is_on = %s,
            mode = %s,
            brightness = %s,
            last_online = %s
        WHERE 
            device_name = %s;
        """
        
        cursor.execute(update_query, (is_on, mode, brightness, now, device_name))
        
        rows_affected = cursor.rowcount

        if rows_affected > 0:
            conn.commit()
            print(f"✅ DB Updated: {device_name} set to is_on={is_on}, mode={mode}")
        else:
            conn.rollback()
            print(f"⚠️ DB Warning: No device found with device_name='{device_name}' to update.")
        
    except Exception as e:
        print(f"❌ DB Error during update: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_all_devices():
    """Lấy danh sách tất cả thiết bị từ DB"""
    conn = None
    devices = []
    try:
        conn = get_db_connection()
        if conn is None: return []

        cursor = conn.cursor()
        
        select_query = """
        SELECT device_name, device_name_display, is_on, mode, brightness
        FROM devices;
        """
        
        cursor.execute(select_query)
        column_names = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            device = dict(zip(column_names, row))
            device['state'] = 'on' if device['is_on'] else 'off'
            device['device_id'] = device['device_name'] 
            del device['is_on'] 
            devices.append(device)
            
        return devices
        
    except Exception as e:
        print(f"❌ DB Error during device retrieval: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_new_device_to_db(device_name, user_id, device_name_display):
    """Thêm một thiết bị mới vào bảng devices"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return False, "Không thể kết nối DB"

        cursor = conn.cursor()
        
        user_id_int = int(user_id) 

        insert_query = """
        INSERT INTO devices (user_id, device_name, device_name_display, mode, is_on, brightness)
        VALUES (%s, %s, %s, 'manual', FALSE, 100)
        RETURNING device_name;
        """
        
        cursor.execute(insert_query, (user_id_int, device_name, device_name_display))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return True, new_id
        
    except psycopg2.errors.UniqueViolation:
        if conn: conn.rollback()
        return False, "Tên thiết bị đã tồn tại."
    except Exception as e:
        print(f"❌ DB Error during device insertion: {e}")
        if conn: conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()


# ============================
# XỬ LÝ MQTT MESSAGES
# ============================
def on_mqtt_message_handler(client, userdata, msg):
    """Callback xử lý nghiệp vụ khi nhận tin nhắn MQTT"""
    try:
        payload = msg.payload.decode()
        print("\n===== MQTT MESSAGE RECEIVED =====")
        print("Topic  :", msg.topic)
        print("Payload:", payload)
        
        try:
            data = json.loads(payload)
            print("Parsed JSON:", data)
            update_device_state(data) # Cập nhật DB
        except json.JSONDecodeError:
            print("Payload is not valid JSON. Cannot update DB.")
            
        print("================================")
    except Exception as e:
        print("Error in on_message:", e)


def publish_command(user_id, device_id, state, mode, brightness=100):
    """Gửi lệnh điều khiển MQTT từ Backend"""
    mqtt_client = get_mqtt_client()
    
    topic = f"home/{user_id}/{device_id}/cmd"
    
    payload = {
        "command": "set",
        "state": state,
        "mode": mode,
        "brightness": brightness,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    mqtt_client.publish(topic, json.dumps(payload))
    
    print("==> MQTT Published")
    print("Topic:", topic)
    print("Payload:", payload)
    
def init_controller():
    """Hàm khởi tạo chính, thiết lập MQTT Client với callback nghiệp vụ"""
    print("Initializing MQTT Controller...")
    # Truyền hàm xử lý nghiệp vụ vào hàm khởi tạo client
    from config.mqtt import init_mqtt_client
    init_mqtt_client(on_mqtt_message_handler)
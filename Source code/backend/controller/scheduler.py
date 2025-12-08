# THÊM: Scheduler controller - Quản lý lịch hẹn giờ bật/tắt đèn
import time
from datetime import datetime
from config.db import get_db_connection
from psycopg2.extras import RealDictCursor


# THÊM: Lấy lịch hẹn giờ từ database theo device_id
def get_schedule(device_id):
    """
    Lấy lịch hẹn giờ hiện tại của thiết bị từ database
    Return: dict với start_time, end_time, is_active, hoặc default values
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        device_id = 1
        cursor.execute(
            "SELECT schedule_id, start_time, end_time, is_active FROM schedules WHERE device_id=%s LIMIT 1",
            (device_id,)
        )
        schedule = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if schedule:
            return {
                "schedule_id": schedule["schedule_id"],
                "start_time": str(schedule["start_time"]) if schedule["start_time"] else "07:00",
                "end_time": str(schedule["end_time"]) if schedule["end_time"] else "22:00",
                "is_active": schedule["is_active"]
            }
        else:
            # Trả về giá trị mặc định nếu chưa có schedule
            return {
                "start_time": "07:00",
                "end_time": "22:00",
                "is_active": False
            }
    except Exception as e:
        print(f"[SCHEDULER] Lỗi lấy schedule: {e}")
        return {
            "start_time": "07:00",
            "end_time": "22:00",
            "is_active": False
        }


# THÊM: Lưu lịch hẹn giờ vào database
def save_schedule(device_id, start_time, end_time):
    """
    Lưu hoặc cập nhật lịch hẹn giờ cho thiết bị
    Args:
        device_id: ID của thiết bị
        start_time: Giờ bật (format "HH:MM")
        end_time: Giờ tắt (format "HH:MM")
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # tach so cuoi trong device_id vidu light1 thanh so 1
        device_num = int(''.join(filter(str.isdigit, device_id)))
        # THÊM: Kiểm tra xem schedule đã tồn tại chưa
        cursor.execute(
            "SELECT schedule_id FROM schedules WHERE device_id=%s",
            (device_num,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # THÊM: Cập nhật schedule hiện có
            device_id = device_num
            cursor.execute(
                """UPDATE schedules 
                   SET start_time=%s, end_time=%s, is_active=TRUE 
                   WHERE device_id=%s""",
                (start_time, end_time, device_id)
            )
            print(f"[SCHEDULER] Cập nhật schedule device {device_id}: {start_time} - {end_time}")
        else:
            # THÊM: Tạo schedule mới
            device_id = device_num
            cursor.execute(
                """INSERT INTO schedules (device_id, start_time, end_time, repeat, brightness, is_active)
                   VALUES (%s, %s, %s, 'none', 100, TRUE)""",
                (device_id, start_time, end_time)
            )
            print(f"[SCHEDULER] Tạo schedule mới device {device_id}: {start_time} - {end_time}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"[SCHEDULER] Lỗi lưu schedule: {e}")
        return False


# THÊM: Xóa lịch hẹn giờ
def delete_schedule(device_id):
    """
    Xóa lịch hẹn giờ của thiết bị
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM schedules WHERE device_id=%s", (device_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[SCHEDULER] Xóa schedule device {device_id}")
        return True
    except Exception as e:
        print(f"[SCHEDULER] Lỗi xóa schedule: {e}")
        return False


# THÊM: Background thread thực thi lịch hẹn giờ
def schedule_executor(socketio, mqtt_client):
    """
    Background thread kiểm tra và thực thi lịch hẹn giờ
    Chạy mỗi 30 giây để kiểm tra xem có giờ nào cần thực thi không
    """
    print("[SCHEDULER] ▶️ Scheduler executor bắt đầu chạy...")
    
    last_executed_on = {}
    last_executed_off = {}
    
    while True:
        try:
            time.sleep(3)  # Kiểm tra mỗi 30 giây
            
            current_time = datetime.now().strftime("%H:%M")
            print(f"[SCHEDULER] ⏰ Kiểm tra lịch lúc {current_time}")
            
            # THÊM: Lấy tất cả các schedule từ database
            try:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute(
                    "SELECT device_id, start_time, end_time, is_active FROM schedules WHERE is_active=TRUE"
                )
                schedules = cursor.fetchall()
                cursor.close()
                conn.close()
                
                # THÊM: Duyệt qua tất cả các schedule hoạt động
                for schedule in schedules:
                    device_id = str(schedule["device_id"])
                    start_time = str(schedule["start_time"])[:5]  # Lấy HH:MM
                    end_time = str(schedule["end_time"])[:5]      # Lấy HH:MM
                    
                    # THÊM: Kiểm tra nếu giờ hiện tại khớp với giờ bật
                    if current_time == start_time:
                        # THÊM: Chỉ thực thi 1 lần khi lần đầu bằng giờ
                        if device_id not in last_executed_on or last_executed_on[device_id] != current_time:
                            print(f"[SCHEDULER] 🟢 Device {device_id}: BẬT đèn lúc {current_time}")
                            
                            # THÊM: Gửi MQTT command để bật đèn
                            topic = f"home/user1/light1/cmd"
                            mqtt_client.publish(topic, '{"state": "on", "mode": "manual"}')
                            
                            # THÊM: Thông báo cho frontend qua Socket.IO
                            socketio.emit("schedule_executed", {
                                "device_id": "light" + device_id,
                                "action": "on",
                                "time": current_time
                            })
                            
                            last_executed_on[device_id] = current_time
                    
                    # THÊM: Kiểm tra nếu giờ hiện tại khớp với giờ tắt
                    elif current_time == end_time:
                        # THÊM: Chỉ thực thi 1 lần khi lần đầu bằng giờ
                        if device_id not in last_executed_off or last_executed_off[device_id] != current_time:
                            print(f"[SCHEDULER] 🔴 Device {device_id}: TẮT đèn lúc {current_time}")
                            
                            # THÊM: Gửi MQTT command để tắt đèn
                            topic = f"home/user1/light1/cmd"
                            mqtt_client.publish(topic, '{"state": "off", "mode": "manual"}')
                            
                            # # THÊM: Thông báo cho frontend qua Socket.IO
                            # socketio.emit("schedule_executed", {
                            #     "device_id": "light" + device_id,
                            #     "action": "off",
                            #     "time": current_time
                            # })
                            
                            last_executed_off[device_id] = current_time
            
            except Exception as db_error:
                print(f"[SCHEDULER] Lỗi query database: {db_error}")
        
        except Exception as e:
            print(f"[SCHEDULER] ⚠️ Lỗi trong schedule_executor: {e}")
            time.sleep(30)

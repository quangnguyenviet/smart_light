import json
from datetime import datetime
from config.db import get_db_connection
from config.web_socket import socketio
import paho.mqtt.client as mqtt

# ====================
# MQTT SETUP
# ====================
MQTT_BROKER = "broker.hivemq.com"  # hoặc IP của HiveMQ broker
MQTT_PORT = 1883
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


# ====================
# UPDATE DATABASE
# ====================
def update_device_state(data):
    device_name = data.get("device_id")
    state = data.get("state")
    mode = data.get("mode")
    brightness = data.get("brightness")
    is_on = (state == "on")
    now = datetime.now()

    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print(f"❌ Cannot connect to DB for device: {device_name}")
            return

        cursor = conn.cursor()
        query = """
            UPDATE devices
            SET is_on = %s, mode = %s, brightness = %s, last_online = %s
            WHERE device_name = %s;
        """
        print(f"📝 Executing query: UPDATE devices SET is_on={is_on}, mode={mode}, brightness={brightness}, last_online={now} WHERE device_name={device_name}")
        cursor.execute(query, (is_on, mode, brightness, now, device_name))
        affected = cursor.rowcount
        if affected > 0:
            conn.commit()
            print(f"✅ Updated {device_name}: is_on={is_on}, mode={mode}, brightness={brightness}")
        else:
            print(f"⚠️ Device not found in DB: {device_name}")
    except Exception as e:
        print(f"❌ DB Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


# ====================
# MQTT CALLBACK (khi có MQTT message)
# ====================
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"[MQTT] Topic={msg.topic} Payload={payload}")

        try:
            data = json.loads(payload)
            update_device_state(data)
            socketio.emit("device_state_update", data) 
            print("🔥 EMIT TO FRONTEND:", data)

        except json.JSONDecodeError:
            print("❌ Invalid JSON")

    except Exception as e:
        print(f"❌ MQTT Callback Error: {e}")



# ====================
# PROCESS API COMMAND (giữ nguyên API nếu muốn)
# ====================
def process_device_command(mqtt_client, data):
    """
    Xử lý command từ API, bao gồm state, mode và brightness.
    """
    user_id = data.get("user_id")
    device_id = data.get("device_id")
    state = data.get("state")
    mode = data.get("mode")
    brightness = data.get("brightness")  # có thể None

    if not user_id or not device_id:
        return {"error": "Missing user_id or device_id"}, 400

    topic = f"home/{user_id}/{device_id}/cmd"
    payload = {
        "command": "set",
        "state": state,
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if brightness is not None:
        payload["brightness"] = brightness

    mqtt_client.publish(topic, json.dumps(payload))
    print("==> MQTT Published:", topic, payload)

    return {"message": "Command sent", "mqtt_topic": topic, "mqtt_payload": payload}, 200



# ====================
# WEBSOCKET HANDLER CHO BRIGHTNESS
# ====================
@socketio.on("brightness_change")  # đồng bộ với frontend
def handle_brightness_command(data):
    device_id = data.get("device_id")
    user_id = data.get("user_id")
    brightness = data.get("brightness")

    if device_id and user_id and brightness is not None:
        topic = f"home/{user_id}/{device_id}/cmd"
        payload = {
            "command": "set",
            "brightness": brightness,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        mqtt_client.publish(topic, json.dumps(payload))
        print(f"🌟 WS -> MQTT Published: {topic} {payload}")

    else:
        print("⚠ Invalid WS brightness payload:", data)

# ====================
# Lấy ds thiết bị từ DB
# ====================

def get_all_devices():
    """Lấy danh sách tất cả devices từ database"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return []

        cursor = conn.cursor()
        query = "SELECT device_id, device_name, is_on, mode, brightness FROM devices;"
        cursor.execute(query)
        devices = cursor.fetchall()
        
        result = []
        for device in devices:
            result.append({
                "device_id": device[0],
                "device_name": device[1],
                "is_on": device[2],
                "mode": device[3],
                "brightness": device[4]
            })
        return result
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return []
    finally:
        if conn:
            conn.close()


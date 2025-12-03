# controller/device.py
import json
from datetime import datetime
from config.db import get_db_connection

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
            return

        cursor = conn.cursor()

        query = """
            UPDATE devices
            SET is_on = %s, mode = %s, brightness = %s, last_online = %s
            WHERE device_name = %s;
        """

        cursor.execute(query, (is_on, mode, brightness, now, device_name))
        affected = cursor.rowcount

        if affected > 0:
            conn.commit()
            print(f"✅ Updated {device_name}")
        else:
            print(f"⚠️ Device not found: {device_name}")

    except Exception as e:
        print(f"❌ DB Error: {e}")
        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


# ====================
# MQTT CALLBACK
# ====================
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"[MQTT] Topic={msg.topic} Payload={payload}")

        try:
            data = json.loads(payload)
            update_device_state(data)
        except json.JSONDecodeError:
            print("❌ Invalid JSON")

    except Exception as e:
        print(f"❌ MQTT Callback Error: {e}")


# ====================
# PROCESS API COMMAND
# ====================
def process_device_command(mqtt_client, data):
    """
    Xử lý command từ API. 
    (app.py chỉ gọi hàm này, không xử lý gì thêm)
    """
    user_id = data.get("user_id")
    device_id = data.get("device_id")
    state = data.get("state")
    mode = data.get("mode")

    if not user_id or not device_id:
        return {"error": "Missing user_id or device_id"}, 400

    topic = f"home/{user_id}/{device_id}/cmd"

    payload = {
        "command": "set",
        "state": state,
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    mqtt_client.publish(topic, json.dumps(payload))

    print("==> MQTT Published:", topic, payload)

    return {
        "message": "Command sent",
        "mqtt_topic": topic,
        "mqtt_payload": payload
    }, 200

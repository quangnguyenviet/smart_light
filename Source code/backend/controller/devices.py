import json
from config.db import get_db_connection
from config.web_socket import socketio
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

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
    now = datetime.now(timezone.utc)

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
# MQTT CALLBACK (khi có MQTT message)
# ====================
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print(f"[MQTT] Topic={msg.topic} Payload={payload}")
        data = json.loads(payload)
        topic = msg.topic
        print("🔔 MQTT Message Received:", topic, data)

        # Nếu là heartbeat
        if topic.endswith("/heartbeat"):
            device_id = data.get("device_id")
            now = datetime.now(timezone.utc)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE devices SET last_online=%s WHERE device_name=%s",
                (now, device_id)
            )
            conn.commit()
            conn.close()
            return

        # Update DB
        update_device_state(data)

        # Emit realtime cho frontend
        socketio.emit("device_state_update", data)  # đổi tên event cho trùng frontend
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

        # **Không emit UI update ở đây nữa**
        # UI sẽ update khi ESP32 publish trạng thái -> on_message -> emit device_state_update
    else:
        print("⚠ Invalid WS brightness payload:", data)


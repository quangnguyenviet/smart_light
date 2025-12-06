from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from threading import Thread
import time

from config.db import get_db_connection
from config.web_socket import socketio
from config.mqtt import create_mqtt_client
from controller.devices import on_message, process_device_command
from time import sleep


OFFLINE_THRESHOLD = 5  # giây

from psycopg2.extras import RealDictCursor

def offline_checker():
    while True:
        try:
            print("Checking for offline devices...")

            now = datetime.now(timezone.utc)   # MUST be timezone-aware

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT device_name, last_online FROM devices")
            devices = cursor.fetchall()

            for device in devices:
                last_online = device["last_online"]
                
                # print ra thời gian hiện tại và last_online để debug
                print(f"Now: {now}, Last online of {device['device_name']}: {last_online}")
                # print ra hiệu số thời gian để debug
                print(f"Time difference (seconds): {(now - last_online).total_seconds() if last_online else 'N/A'}")

                if last_online and (now - last_online).total_seconds() > OFFLINE_THRESHOLD:

                    cursor.execute(
                        "UPDATE devices SET is_on=FALSE WHERE device_name=%s",
                        (device["device_name"],)
                    )

                    data = {
                        "device_id": device["device_name"],
                        "state": "Offline",
                        "mode": None,
                        "brightness": None
                    }

                    print("⚠️ Device offline:", device["device_name"])
                    socketio.emit("device_state_update", data)

            conn.commit()
            conn.close()

        except Exception as e:
            print("🔥 ERROR in offline_checker:", str(e))

        time.sleep(30)


# --- Bắt đầu thread khi server khởi chạy ---
def start_background_tasks():
    Thread(target=offline_checker, daemon=True).start()

app = Flask(__name__)
CORS(app)

# init socketio
socketio.init_app(app)

# init mqtt
mqtt_client = create_mqtt_client(on_message)
mqtt_client.subscribe("home/+/+/state")
mqtt_client.loop_start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/device/command", methods=["POST"])
def device_command():
    data = request.json
    response, status = process_device_command(mqtt_client, data)
    return jsonify(response), status


def emit_test():
    while True:
        print("Emitting test...")
        socketio.emit("device_state_update", {"msg": "hello"})
        sleep(3)
if __name__ == "__main__":
    print("Server running...")
    # socketio.start_background_task(target=emit_test)
    socketio.start_background_task(target=offline_checker)
    socketio.run(app, host="0.0.0.0", port=5000)

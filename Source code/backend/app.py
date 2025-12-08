from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from threading import Thread
import time
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

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
                        "state": "offline",
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
# THÊM: import các hàm xử lý đăng nhập/đăng kí từ controller auth
from controller.auth import register_user, login_user, get_user_by_id
from config.db import get_db_connection

# Device controllers
from controller.devices import on_message, process_device_command, get_all_devices

# User controllers (login/register/logout)
from controller.user_controller import (
    handle_login,
    handle_register,
    handle_logout,
    handle_current_user,
    require_login
)

app = Flask(__name__)
app.secret_key = 'smart_light_secret_key_2025'
CORS(app)

# =========================================
# INIT SOCKET.IO
# =========================================
socketio.init_app(app, cors_allowed_origins="*")

# =========================================
# INIT MQTT
# =========================================
mqtt_client = create_mqtt_client(on_message)
mqtt_client.subscribe("home/+/+/state")
mqtt_client.loop_start()

# =========================================
# USER ROUTES
# =========================================
@app.route("/login", methods=["GET", "POST"])
def login_page():
    return handle_login()


@app.route("/register", methods=["GET", "POST"])
def register_page():
    return handle_register()


@app.route("/logout", methods=["POST"])
def logout():
    return handle_logout()


@app.route("/api/current-user", methods=["GET"])
def current_user():
    return handle_current_user()


# =========================================
# MAIN ROUTES
# =========================================
@app.route("/")
@require_login
def home():
    return render_template("dashboard.html")


@app.route("/control/<device_id>")
@require_login
def control(device_id):
    print("hello")
    return render_template("index.html", device_id=device_id)


# =========================================
# API — DEVICES
# =========================================
@app.route("/api/devices", methods=["GET"])
def get_devices():
    return jsonify(get_all_devices()), 200


@app.route("/api/device/command", methods=["POST"])
def device_command():
    response, status = process_device_command(mqtt_client, request.json)
    return jsonify(response), status



if __name__ == "__main__":
    db_conn = get_db_connection()
    if db_conn:
        print("DB OK")
        db_conn.close()
    socketio.start_background_task(target=offline_checker)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True,use_reloader=False)

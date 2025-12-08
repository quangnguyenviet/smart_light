from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from config.web_socket import socketio
from config.mqtt import create_mqtt_client
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

    socketio.run(app, host="0.0.0.0", port=5000, debug=True,use_reloader=False)

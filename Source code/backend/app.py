from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from config.web_socket import socketio
from config.mqtt import create_mqtt_client
from config.db import get_db_connection
from controller.devices import on_message, process_device_command, get_all_devices

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
    return render_template("dashboard.html")

@app.route("/control/<device_id>")
def control(device_id):
    return render_template("index.html", device_id=device_id)

@app.route("/api/devices", methods=["GET"])
def get_devices():
    devices = get_all_devices()
    return jsonify(devices), 200

@app.route("/api/device/command", methods=["POST"])
def device_command():
    data = request.json
    response, status = process_device_command(mqtt_client, data)
    return jsonify(response), status
# Thêm đoạn này vào cuối app.py (trước if __name__ == "__main__") để test emit websocket
# @app.route("/test-emit")
# def test_emit():
#     """Gọi http://localhost:5000/test-emit để bắn 1 event websocket"""
#     fake_data = {
#         "device_id": "light1",
#         "device_name": "light1",
#         "state": "on",
#         "mode": "auto",
#         "brightness": 75
#     }
    
#     socketio.emit("device_state_update", fake_data)
#     print("TEST EMIT: Đã bắn device_state_update", fake_data)
    
#     return "Đã emit thành công! Check console + giao diện index.html"
if __name__ == "__main__":
    # Test DB connection
    print("\n" + "="*50)
    print("🔧 SMART LIGHT CONTROL SERVER")
    print("="*50)
    
    db_conn = get_db_connection()
    if db_conn:
        print("✅ Database connection: SUCCESS")
        db_conn.close()
    else:
        print("❌ Database connection: FAILED")
    
    print(f"🌐 Web Server: http://localhost:5000")
    print(f"📊 Dashboard: http://localhost:5000/")
    print(f"🚀 Server running on http://0.0.0.0:5000")
    print("="*50 + "\n")
    
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
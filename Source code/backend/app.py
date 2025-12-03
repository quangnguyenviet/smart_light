from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Import các hàm nghiệp vụ từ controller
from controller.devices import (
    init_controller, 
    publish_command, 
    get_all_devices, 
    add_new_device_to_db
) 
import json 

app = Flask(__name__)
CORS(app)

# ============================
# ROUTE TRẢ VỀ TRANG HTML
# ============================
@app.route("/")
def home():
    """Trả về trang điều khiển chính (index.html)"""
    return render_template("index.html")

# ==================================
# API: Lấy danh sách thiết bị (GET)
# ==================================
@app.route("/api/devices", methods=["GET"])
def list_devices():
    """Lấy danh sách thiết bị và trạng thái hiện tại từ DB"""
    devices = get_all_devices()
    return jsonify(devices), 200

# ==================================
# API: Thêm thiết bị mới (POST)
# ==================================
@app.route("/api/devices", methods=["POST"])
def add_device():
    """Thêm một thiết bị mới vào database"""
    data = request.json
    device_name = data.get("device_name")
    device_name_display = data.get("device_name_display")
    user_id = "1" 

    if not device_name or not device_name_display:
        return jsonify({"error": "Thiếu device_name hoặc device_name_display"}), 400
    
    if not device_name.isalnum():
        return jsonify({"error": "ID thiết bị phải là chữ cái và số (không dấu cách/ký tự đặc biệt)."}), 400

    success, result = add_new_device_to_db(device_name, user_id, device_name_display)
    
    if success:
        publish_command(user_id, device_name, "off", "manual", 100) 
        return jsonify({"message": f"Thêm thiết bị '{device_name_display}' thành công.", "device_id": result}), 201
    else:
        return jsonify({"error": result}), 409

# ============================
# API: Nhận lệnh từ frontend → Publish MQTT (POST)
# ============================
@app.route("/api/device/command", methods=["POST"])
def device_command():
    """Nhận lệnh điều khiển từ frontend và publish lên MQTT"""
    data = request.json

    user_id = data.get("user_id", "light1")
    device_id = data.get("device_id")
    state = data.get("state")
    mode = data.get("mode")
    brightness = data.get("brightness", 100)

    if not user_id or not device_id:
        return jsonify({"error": "Missing user_id or device_id"}), 400

    publish_command(user_id, device_id, state, mode, brightness)

    return jsonify({
        "message": "MQTT command sent successfully",
        "device_id": device_id
    }), 200


# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    # Khởi tạo toàn bộ controller (bao gồm MQTT)
    init_controller() 
    print("Flask + HiveMQ MQTT Server Running...")
    
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
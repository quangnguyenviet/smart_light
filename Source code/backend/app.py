# app.py
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from config.mqtt import create_mqtt_client
from controller.devices import on_message, process_device_command

app = Flask(__name__)
CORS(app)

# Init MQTT
mqtt_client = create_mqtt_client(on_message)
mqtt_client.subscribe("home/+/+/state")
mqtt_client.loop_start()

# ============================
# ROUTES ONLY
# ============================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/device/command", methods=["POST"])
def device_command():
    data = request.json
    response, status = process_device_command(mqtt_client, data)
    return jsonify(response), status


if __name__ == "__main__":
    print("Server running...")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

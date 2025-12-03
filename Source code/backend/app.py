from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from config.web_socket import socketio
from config.mqtt import create_mqtt_client
from controller.devices import on_message, process_device_command

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

if __name__ == "__main__":
    print("Server running...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

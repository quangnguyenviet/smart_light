import paho.mqtt.client as mqtt
import json
import ssl
from datetime import datetime

# ============================
# MQTT CONFIG
# ============================

USE_HIVEMQ_CLOUD = False
HIVEMQ_PUBLIC_BROKER = "broker.hivemq.com"
HIVEMQ_PUBLIC_PORT = 1883

HIVEMQ_CLOUD_HOST = "your-host.s2.eu.hivemq.cloud"
HIVEMQ_CLOUD_PORT = 8883
HIVEMQ_USERNAME = "your-username"
HIVEMQ_PASSWORD = "your-password"

# Khởi tạo MQTT Client toàn cục (sẽ được import vào controller)
mqtt_client = mqtt.Client()


def init_mqtt_client(on_message_callback):
    """
    Thiết lập kết nối và loop cho MQTT Client.
    on_message_callback là hàm xử lý nghiệp vụ khi nhận tin nhắn.
    """
    global mqtt_client
    
    # Gán hàm xử lý nghiệp vụ cho callback
    mqtt_client.on_message = on_message_callback  

    if USE_HIVEMQ_CLOUD:
        print("==> Using HiveMQ Cloud with SSL")
        mqtt_client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
            ciphers=None
        )
        mqtt_client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)
        mqtt_client.connect(HIVEMQ_CLOUD_HOST, HIVEMQ_CLOUD_PORT)
    else:
        print("==> Using HiveMQ Public Broker")
        mqtt_client.connect(HIVEMQ_PUBLIC_BROKER, HIVEMQ_PUBLIC_PORT)

    # Subscribe tất cả topic trạng thái của các thiết bị
    mqtt_client.subscribe("home/+/+/state")
    mqtt_client.loop_start()

def get_mqtt_client():
    """Trả về instance của MQTT client để gửi lệnh"""
    return mqtt_client
# config/mqtt.py
import ssl
import paho.mqtt.client as mqtt

USE_HIVEMQ_CLOUD = False

HIVEMQ_PUBLIC_BROKER = "broker.hivemq.com"
HIVEMQ_PUBLIC_PORT = 1883

HIVEMQ_CLOUD_HOST = "your-host.s2.eu.hivemq.cloud"
HIVEMQ_CLOUD_PORT = 8883
HIVEMQ_USERNAME = "your-username"
HIVEMQ_PASSWORD = "your-password"

def create_mqtt_client(on_message_callback):
    client = mqtt.Client()
    client.on_message = on_message_callback

    if USE_HIVEMQ_CLOUD:
        print("==> Using HiveMQ Cloud")
        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS
        )
        client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)
        client.connect(HIVEMQ_CLOUD_HOST, HIVEMQ_CLOUD_PORT)

    else:
        print("==> Using HiveMQ Public Broker")
        client.connect(HIVEMQ_PUBLIC_BROKER, HIVEMQ_PUBLIC_PORT)

    return client

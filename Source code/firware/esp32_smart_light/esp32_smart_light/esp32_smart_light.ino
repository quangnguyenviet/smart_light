#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define LED_PIN  12     // LED nối vào chân GPIO12 (qua Mosfet/220Ω)

// ============================
// WiFi Cấu Hình
// ============================
const char* WIFI_SSID     = "Congminh";
const char* WIFI_PASSWORD = "phamminh";

// ============================
// MQTT HiveMQ Public Broker
// ============================
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

// ============================
// Chủ đề MQTT ESP32 sẽ subscribe
// ============================
String user_id   = "light1";
String device_id = "light1";
String topic_cmd   = "home/" + user_id + "/" + device_id + "/cmd";
String topic_state = "home/" + user_id + "/" + device_id + "/state";

// WiFi + MQTT Clients
WiFiClient espClient;
PubSubClient client(espClient);

// ======================================================
// Hàm gửi trạng thái thực tế về server
// ======================================================
void publishState(String state, String mode, int brightness = 100) {
    StaticJsonDocument<256> doc;
    doc["device_id"]  = device_id;
    doc["state"]      = state;
    doc["mode"]       = mode;
    doc["brightness"] = brightness;

    // Timestamp đơn giản (giây kể từ ESP32 khởi động)
    unsigned long t = millis() / 1000;
    doc["timestamp"] = String(t);

    char buffer[256];
    size_t n = serializeJson(doc, buffer);
    client.publish(topic_state.c_str(), buffer, n);

    Serial.print("📤 Published state: ");
    Serial.println(buffer);
}

// ======================================================
// Callback: Khi ESP32 nhận message từ MQTT
// ======================================================
void callback(char* topic, byte* payload, unsigned int length) {
    Serial.println("===== MQTT MESSAGE RECEIVED =====");
    Serial.print("Topic: ");
    Serial.println(topic);

    // convert payload thành chuỗi
    String msg;
    for (int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    Serial.print("Payload: ");
    Serial.println(msg);

    // parse JSON
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, msg);

    if (error) {
        Serial.println("❌ JSON parse failed!");
        return;
    }

    String command = doc["command"] | "";
    String state   = doc["state"]   | "";
    String mode    = doc["mode"]    | "";

    Serial.println("Command: " + command);
    Serial.println("State  : " + state);
    Serial.println("Mode   : " + mode);

    // ============================
    // Điều khiển LED / Mosfet
    // ============================
    if (state == "on") {
        digitalWrite(LED_PIN, HIGH);
        Serial.println("💡 LED: BẬT");
    } 
    else if (state == "off") {
        digitalWrite(LED_PIN, LOW);
        Serial.println("💡 LED: TẮT");
    }

    // ============================
    // Gửi trạng thái thực tế về server
    // ============================
    publishState(state, mode, 100);  // brightness mặc định 100
}

// ============================
// Kết nối WiFi
// ============================
void setupWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
}

// ============================
// Kết nối MQTT
// ============================
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("Connecting to MQTT... ");

        // Tạo clientID ngẫu nhiên
        String clientId = "ESP32_" + String(random(0xffff), HEX);

        if (client.connect(clientId.c_str())) {
            Serial.println("CONNECTED!");
            client.subscribe(topic_cmd.c_str());
            Serial.print("Subscribed to topic: ");
            Serial.println(topic_cmd);
        } 
        else {
            Serial.print("FAILED, rc=");
            Serial.print(client.state());
            Serial.println(" → retry in 3 sec");
            delay(3000);
        }
    }
}

// ============================
// Setup
// ============================
void setup() {
    Serial.begin(115200);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    setupWiFi();

    client.setServer(MQTT_BROKER, MQTT_PORT);
    client.setCallback(callback);
}

// ============================
// Loop
// ============================
void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        setupWiFi();
    }

    if (!client.connected()) {
        reconnectMQTT();
    }

    client.loop();
}

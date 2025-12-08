#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ============================
// Định nghĩa chân điều khiển
// ============================
#define MOSFET_LED_PIN  12      // Chân điều khiển Mosfet/Đèn (PWM)
#define DIRECT_LED_PIN  19      // Chân điều khiển LED trực tiếp (KHÔNG qua Mosfet)
#define PIR_INPUT_PIN   5       // Chân GPIO kết nối với HC-SR501

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
// Chủ đề MQTT ESP32 sẽ subscribe/publish
// ============================
String user_id   = "light1";
String device_id = "light1";
String topic_cmd   = "home/" + user_id + "/" + device_id + "/cmd";
String topic_state = "home/" + user_id + "/" + device_id + "/state";
String topic_heartbeat = "home/" + user_id + "/" + device_id + "/heartbeat";


// cau hinh hearbeat
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_INTERVAL = 10000; // 10 giây

// ============================
// WiFi + MQTT Clients
// ============================
WiFiClient espClient;
PubSubClient client(espClient);

// ============================
// Trạng thái đèn & độ sáng
// ============================
String current_state = "off";    // "on" hoặc "off"
String current_mode  = "manual"; // "manual" hoặc "auto"
int    current_brightness = 100; // 0 - 100 (%) (sau đó map ra 0 - 255 cho PWM)

// Thời gian tự động tắt khi hết chuyển động
unsigned long lastMotionTime = 0;
const unsigned long AUTO_OFF_DELAY_MS = 4000; // 4 giây

// ============================
// Gửi trạng thái thực tế lên MQTT
// ============================
void publishState() {
    StaticJsonDocument<256> doc;
    doc["device_id"]  = device_id;
    doc["state"]      = current_state;
    doc["mode"]       = current_mode;
    doc["brightness"] = current_brightness;
    doc["timestamp"]  = String(millis() / 1000);

    char buffer[256];
    size_t n = serializeJson(doc, buffer);
    client.publish(topic_state.c_str(), buffer, n);
    Serial.print("📤 Published state: ");
    Serial.println(buffer);
}

// ============================
// Điều khiển LED PWM
// ============================
void setLightState(String newState, int brightness = -1, String source = "") {
    bool updated = false;

    if (newState != current_state) {
        current_state = newState;
        updated = true;
        Serial.println("💡 LED state: " + newState + " (" + source + ")");
    }

    if (brightness >= 0 && brightness != current_brightness) {
        current_brightness = brightness;
        updated = true;
        Serial.println("💡 LED brightness: " + String(current_brightness) + " (" + source + ")");
    }

    // Tính giá trị PWM
    int pwmValue;
    if (current_state == "on") {
        // Map độ sáng từ 0-100% sang 0-255 cho PWM
        pwmValue = map(current_brightness, 0, 100, 0, 255); 
    } else {
        pwmValue = 0;
    }
    
    // Áp dụng cho chân 12 (DÙNG MOSFET)
    // Giá trị PWM cao (255) là TẮT (nếu dùng Mosfet p-channel) hoặc SÁNG (nếu dùng Mosfet n-channel)
    // Giả sử dùng Mosfet n-channel: HIGH/255 = SÁNG, LOW/0 = TẮT
    analogWrite(MOSFET_LED_PIN, pwmValue); 

    // Áp dụng cho chân 19 (TRỰC TIẾP/KHÔNG MOSFET)
    // Vì không qua Mosfet, chân này điều khiển LED/tải trực tiếp: HIGH/255 = SÁNG, LOW/0 = TẮT
    analogWrite(DIRECT_LED_PIN, pwmValue); 

    Serial.println("⚙️ PWM set to: " + String(pwmValue) + " on pins 12 (MOSFET) and 19 (DIRECT).");


    if (updated) publishState();
}

// ============================
// MQTT Callback
// ============================
void callback(char* topic, byte* payload, unsigned int length) {
    Serial.println("===== MQTT MESSAGE RECEIVED =====");
    String msg;
    for (int i = 0; i < length; i++) msg += (char)payload[i];
    Serial.println("Payload: " + msg);

    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, msg);
    if (error) {
        Serial.println("❌ JSON parse failed!");
        return;
    }

    String state_cmd = doc["state"] | "";
    String mode_cmd  = doc["mode"]  | "";
    int brightness_cmd = doc["brightness"] | -1;

    // Cập nhật mode
    if (mode_cmd.length() > 0 && current_mode != mode_cmd) {
        current_mode = mode_cmd;
        Serial.println("⚙️ MODE CHANGED to: " + current_mode);
    }

    // Chỉ xử lý lệnh bật/tắt khi ở manual, brightness luôn được update
    if (current_mode == "manual") {
        if (state_cmd == "on" || state_cmd == "off") {
            setLightState(state_cmd, brightness_cmd, "MQTT_MANUAL");
        } else if (brightness_cmd >= 0) {
            setLightState("on", brightness_cmd, "MQTT_BRIGHTNESS"); 
        }
    } else { // AUTO
        // Cho phép override tắt đèn
        if (state_cmd == "off") {
            setLightState("off", -1, "MQTT_OVERRIDE");
        }
        // brightness vẫn update nếu có
        if (brightness_cmd >= 0) {
            setLightState(current_state, brightness_cmd, "MQTT_BRIGHTNESS");
        }
    }

    publishState();
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
    Serial.println("\nWiFi connected! IP: " + WiFi.localIP().toString());
}

// ============================
// Kết nối MQTT
// ============================
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("Connecting to MQTT... ");
        String clientId = "ESP32_" + String(random(0xffff), HEX);
        if (client.connect(clientId.c_str())) {
            Serial.println("CONNECTED!");
            client.subscribe(topic_cmd.c_str()); 
            publishState(); 
        } else {
            Serial.print("FAILED, rc=");
            Serial.print(client.state());
            Serial.println(" → retry in 3 sec");
            delay(3000);
        }
    }
}

// ============================
// Gửi heartbeat
// ============================
void publishHeartbeat() {
    StaticJsonDocument<128> doc;
    doc["device_id"] = device_id;
    doc["timestamp"] = String(millis() / 1000);

    char buffer[128];
    size_t n = serializeJson(doc, buffer);
    client.publish(topic_heartbeat.c_str(), buffer, n);
    Serial.print("💓 Heartbeat sent: ");
    Serial.println(buffer);
}

// ============================
// Setup
// ============================
void setup() {
    Serial.begin(115200);
    
    // Thiết lập các chân LED
    pinMode(MOSFET_LED_PIN, OUTPUT);
    analogWrite(MOSFET_LED_PIN, 0); // Tắt đèn ban đầu

    pinMode(DIRECT_LED_PIN, OUTPUT);
    analogWrite(DIRECT_LED_PIN, 0); // Tắt đèn ban đầu

    pinMode(PIR_INPUT_PIN, INPUT);

    setupWiFi();
    client.setServer(MQTT_BROKER, MQTT_PORT);
    client.setCallback(callback);
}

// ============================
// Loop
// ============================
void loop() {
    // Đảm bảo kết nối
    if (WiFi.status() != WL_CONNECTED) setupWiFi();
    if (!client.connected()) reconnectMQTT();
    client.loop();

    // Xử lý chế độ AUTO
    if (current_mode == "auto") {
        int pirState = digitalRead(PIR_INPUT_PIN);
        if (pirState == HIGH) {
            lastMotionTime = millis(); 
            setLightState("on", current_brightness, "PIR_DETECT");
        } else if (current_state == "on" && millis() - lastMotionTime > AUTO_OFF_DELAY_MS) {
            setLightState("off", -1, "PIR_TIMEOUT");
        }
    }

    // Gửi heartbeat mỗi 10 giây
    if (millis() - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
        publishHeartbeat();
        lastHeartbeatTime = millis();
    }

    delay(50);
}
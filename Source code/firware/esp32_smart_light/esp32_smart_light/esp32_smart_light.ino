#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ============================
// Khai báo chân
// ============================
#define LED1_PIN 12
#define LED2_PIN 19
#define PIR_INPUT_PIN 5

// ============================
// WiFi
// ============================
const char* WIFI_SSID     = "Congminh";
const char* WIFI_PASSWORD = "phamminh";

// ============================
// MQTT
// ============================
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

String user_id = "user1";

String device1_id = "light1";
String device2_id = "light2";

String topic_cmd_1   = "home/" + user_id + "/" + device1_id + "/cmd";
String topic_state_1 = "home/" + user_id + "/" + device1_id + "/state";

String topic_cmd_2   = "home/" + user_id + "/" + device2_id + "/cmd";
String topic_state_2 = "home/" + user_id + "/" + device2_id + "/state";

// Heartbeat
String topic_heartbeat = "home/" + user_id + "/heartbeat";
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_INTERVAL = 5000;

// ============================
// Trạng thái từng đèn
// ============================
struct Light {
    String state = "off";     // "on" / "off"
    String mode = "manual";   // "manual" / "auto"
    int brightness = 100;     // %
};

Light light1;
Light light2;

unsigned long lastMotionTime = 0;
const unsigned long AUTO_OFF_DELAY_MS = 4000;

WiFiClient espClient;
PubSubClient client(espClient);

// ============================
// Publish STATE
// ============================
void publishState(Light &l, String topic, String device_id) {
    StaticJsonDocument<256> doc;

    doc["device_id"]  = device_id;
    doc["state"]      = l.state;
    doc["brightness"] = l.brightness;
    doc["mode"]       = l.mode;
    doc["timestamp"]  = millis() / 1000;

    char buffer[256];
    size_t n = serializeJson(doc, buffer);
    client.publish(topic.c_str(), buffer, n);

    Serial.println("Published state to " + topic + ": " + String(buffer));
}

// ============================
// Điều khiển đèn
// ============================
void setLight(Light &l, int pin, String newState, int brightness, String source) {
    bool changed = false;

    if (newState != "" && newState != l.state) {
        l.state = newState;
        changed = true;
    }
    if (brightness >= 0 && brightness != l.brightness) {
        l.brightness = brightness;
        changed = true;
    }

    int pwm = (l.state == "on") ? map(l.brightness, 0, 100, 0, 255) : 0;
    analogWrite(pin, pwm);

    if (changed) {
        Serial.println("[" + source + "] Updated light: state=" + l.state + " brightness=" + l.brightness);
    }
}

// ============================
// MQTT Callback
// ============================
void callback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (int i = 0; i < length; i++) msg += (char)payload[i];

    Serial.println("MQTT received [" + String(topic) + "]: " + msg);

    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, msg)) {
        Serial.println("Failed to parse JSON!");
        return;
    }

    String state_cmd      = doc["state"] | "";
    int brightness_cmd    = doc["brightness"] | -1;
    String mode_cmd       = doc["mode"] | "";

    String topicStr = String(topic);

    // ---------- ĐÈN 1 ----------
    if (topicStr == topic_cmd_1) {
        Serial.println("Processing command for light1");

        if (mode_cmd != "") light1.mode = mode_cmd;

        if (light1.mode == "manual") {
            if (state_cmd == "on" || state_cmd == "off") {
                setLight(light1, LED1_PIN, state_cmd, brightness_cmd, "light1");
            } else if (brightness_cmd >= 0) {
                setLight(light1, LED1_PIN, "on", brightness_cmd, "light1_brt");
            }
        } else {
            if (state_cmd == "off") setLight(light1, LED1_PIN, "off", -1, "auto_override");
            if (brightness_cmd >= 0) setLight(light1, LED1_PIN, "", brightness_cmd, "auto_brt");
        }

        publishState(light1, topic_state_1, device1_id);
    }

    // ---------- ĐÈN 2 ----------
    if (topicStr == topic_cmd_2) {
        Serial.println("Processing command for light2");

        if (mode_cmd != "") light2.mode = mode_cmd;

        if (light2.mode == "manual") {
            if (state_cmd == "on" || state_cmd == "off") {
                setLight(light2, LED2_PIN, state_cmd, brightness_cmd, "light2");
            } else if (brightness_cmd >= 0) {
                setLight(light2, LED2_PIN, "on", brightness_cmd, "light2_brt");
            }
        } else {
            if (state_cmd == "off") setLight(light2, LED2_PIN, "off", -1, "auto_override2");
            if (brightness_cmd >= 0) setLight(light2, LED2_PIN, "", brightness_cmd, "auto_brt2");
        }

        publishState(light2, topic_state_2, device2_id);
    }
}

// ============================
// WiFi
// ============================
void setupWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi connected! IP: " + WiFi.localIP().toString());
}

// ============================
// MQTT
// ============================
void reconnectMQTT() {
    while (!client.connected()) {
        String clientId = "ESP32_" + String(random(0xffff), HEX);

        Serial.println("Connecting to MQTT broker...");
        if (client.connect(clientId.c_str())) {
            Serial.println("MQTT connected");
            client.subscribe(topic_cmd_1.c_str());
            client.subscribe(topic_cmd_2.c_str());

            publishState(light1, topic_state_1, device1_id);
            publishState(light2, topic_state_2, device2_id);
        } else {
            Serial.print("MQTT connect failed, rc=");
            Serial.print(client.state());
            Serial.println(". Retrying in 2s");
            delay(2000);
        }
    }
}

// ============================
// Heartbeat
// ============================
void publishHeartbeat() {
    StaticJsonDocument<128> doc;
    doc["timestamp"] = millis() / 1000;

    char buffer[128];
    size_t n = serializeJson(doc, buffer);
    client.publish(topic_heartbeat.c_str(), buffer, n);

    Serial.println("Heartbeat published: " + String(buffer));
}

// ============================
// Setup
// ============================
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("ESP32 starting...");

    pinMode(LED1_PIN, OUTPUT);
    pinMode(LED2_PIN, OUTPUT);
    analogWrite(LED1_PIN, 0);
    analogWrite(LED2_PIN, 0);

    pinMode(PIR_INPUT_PIN, INPUT);

    setupWiFi();
    client.setServer(MQTT_BROKER, MQTT_PORT);
    client.setCallback(callback);
}

// ============================
// Loop
// ============================
void loop() {
    if (WiFi.status() != WL_CONNECTED) setupWiFi();
    if (!client.connected()) reconnectMQTT();
    client.loop();

    // AUTO mode cho ĐÈN 1
    if (light1.mode == "auto") {
        int pirState = digitalRead(PIR_INPUT_PIN);
        Serial.println("PIR state: " + String(pirState));

        if (pirState == HIGH) {
            lastMotionTime = millis();
            setLight(light1, LED1_PIN, "on", light1.brightness, "pir");
        } else if (light1.state == "on" && millis() - lastMotionTime > AUTO_OFF_DELAY_MS) {
            setLight(light1, LED1_PIN, "off", -1, "pir_timeout");
        }
    }

    if (millis() - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
        publishHeartbeat();
        lastHeartbeatTime = millis();
    }

    delay(20);
}
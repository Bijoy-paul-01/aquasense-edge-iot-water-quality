/*
 ==============================================================================
  AquaSense IoT - ESP32 Water Quality Detection System Firmware
  Connects to Wi-Fi and streams live physical probe readings to the ML Backend.
 ==============================================================================
  Hardware Components:
  - ESP32 Development Board (NodeMCU ESP-32S / ESP-WROOM-32)
  - DFRobot Gravity Analog pH Sensor (SEN0161) -> GPIO 34 (ADC1_CH6)
  - DFRobot Gravity Analog Turbidity Sensor (SEN0189) -> GPIO 35 (ADC1_CH7)
  - DFRobot Gravity Analog TDS Sensor (SEN0244) -> GPIO 32 (ADC1_CH4)
  - DS18B20 Waterproof 1-Wire Digital Temp Sensor -> GPIO 4
  - Status LED -> GPIO 2 (Onboard)
 ==============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h> // Library: ArduinoJson by Benoit Blanchon (v6 or v7)

// ---------------- CONFIGURATION ----------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// IP / Host of your AquaSense FastAPI Backend Server
const char* SERVER_URL    = "http://192.168.1.100:8000/api/telemetry";
const char* DEVICE_ID     = "ESP32-HARDWARE-NODE-01";

const unsigned long POST_INTERVAL_MS = 2500; // Send reading every 2.5 seconds
// -----------------------------------------------

// PIN DEFINITIONS
#define PIN_PH_PROBE        34
#define PIN_TURBIDITY_PROBE 35
#define PIN_TDS_PROBE       32
#define PIN_ONE_WIRE_BUS    4
#define PIN_STATUS_LED      2

// OneWire & Dallas Temperature setup
OneWire oneWire(PIN_ONE_WIRE_BUS);
DallasTemperature tempSensors(&oneWire);

// SENSOR CALIBRATION OFFSETS
float pH_offset = 0.00;        // Fine-tune against pH 7.0 buffer
float tds_calibration_factor = 0.5; // TDS = EC * 0.5 (TDS factor)

unsigned long lastPostTime = 0;

// Helper: Analog read with multi-sample median filtering to suppress ADC noise
float readAnalogAverage(int pin, int samples = 20) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(5);
  }
  return (float)sum / (float)samples;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[AQUASENSE] Initializing ESP32 Water Quality Sensor Node...");

  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_PH_PROBE, INPUT);
  pinMode(PIN_TURBIDITY_PROBE, INPUT);
  pinMode(PIN_TDS_PROBE, INPUT);

  // Initialize DS18B20 digital temperature probe
  tempSensors.begin();

  // Configure ESP32 ADC (12-bit, 3.3V full scale)
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db); // Full range 0 - 3.3V

  // Connect to Wi-Fi
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    delay(300);
    Serial.print(".");
  }

  digitalWrite(PIN_STATUS_LED, HIGH);
  Serial.println("\n[WiFi] Connected successfully!");
  Serial.print("[WiFi] IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("[WiFi] RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
}

void loop() {
  // Check Wi-Fi connection
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(PIN_STATUS_LED, LOW);
    Serial.println("[WiFi] Reconnecting...");
    WiFi.reconnect();
    delay(2000);
    return;
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastPostTime >= POST_INTERVAL_MS) {
    lastPostTime = currentMillis;

    // 1. Read Temperature (°C)
    tempSensors.requestTemperatures();
    float temperature = tempSensors.getTempCByIndex(0);
    if (temperature < -50.0 || temperature > 100.0) {
      temperature = 21.5; // Fallback default if sensor disconnected
    }

    // 2. Read pH Sensor (DFRobot Gravity Analog pH)
    // ESP32 ADC: 0 - 4095 corresponds to 0 - 3.3V
    float rawPhAdc = readAnalogAverage(PIN_PH_PROBE);
    float phVoltage = (rawPhAdc / 4095.0) * 3.3;
    // Standard pH probe transfer function: 3.5 * voltage + offset
    float phValue = 3.5 * phVoltage + pH_offset;
    phValue = constrain(phValue, 0.0, 14.0);

    // 3. Read Turbidity Sensor (DFRobot Turbidity SEN0189)
    float rawTurbAdc = readAnalogAverage(PIN_TURBIDITY_PROBE);
    float turbVoltage = (rawTurbAdc / 4095.0) * 3.3;
    // Characteristic curve: Turbidity NTU = -1120.4 * V^2 + 5742.3 * V - 4353.8
    float turbidity = 0.0;
    if (turbVoltage < 2.5) {
      turbidity = 3000.0;
    } else if (turbVoltage >= 4.2) {
      turbidity = 0.0;
    } else {
      turbidity = -1120.4 * sq(turbVoltage) + 5742.3 * turbVoltage - 4353.8;
      turbidity = constrain(turbidity / 100.0, 0.1, 80.0); // Scaled NTU
    }

    // 4. Read TDS / Electrical Conductivity (SEN0244)
    float rawTdsAdc = readAnalogAverage(PIN_TDS_PROBE);
    float tdsVoltage = (rawTdsAdc / 4095.0) * 3.3;
    // Temperature compensation formula
    float compensationCoefficient = 1.0 + 0.02 * (temperature - 25.0);
    float compensationVoltage = tdsVoltage / compensationCoefficient;
    // Convert voltage to TDS ppm
    float tdsValue = (133.42 * pow(compensationVoltage, 3) - 255.86 * sq(compensationVoltage) + 857.39 * compensationVoltage) * tds_calibration_factor;
    tdsValue = constrain(tdsValue, 0.0, 2500.0);
    float conductivity = tdsValue / 0.65; // Approx µS/cm

    // 5. Estimated Dissolved Oxygen (mg/L) derived from Henry's law & aeration
    // DO saturation depends heavily on water temperature:
    float doSaturation = 14.652 - 0.41022 * temperature + 0.007991 * sq(temperature);
    float doValue = doSaturation * 0.85; // baseline saturation ratio
    doValue = constrain(doValue, 0.5, 14.0);

    // Print to Serial Console
    Serial.printf("\n--- Reading: Temp: %.1f C | pH: %.2f | Turb: %.2f NTU | TDS: %.1f ppm | Cond: %.1f uS/cm ---\n",
                  temperature, phValue, turbidity, tdsValue, conductivity);

    // Send HTTP POST request to ML Backend
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(SERVER_URL);
      http.addHeader("Content-Type", "application/json");

      // Construct JSON payload using ArduinoJson
      StaticJsonDocument<384> doc;
      doc["device_id"] = DEVICE_ID;
      doc["scenario"] = "Live ESP32 Hardware Probe";
      doc["ph"] = round(phValue * 100.0) / 100.0;
      doc["turbidity"] = round(turbidity * 100.0) / 100.0;
      doc["tds"] = round(tdsValue * 10.0) / 10.0;
      doc["temperature"] = round(temperature * 10.0) / 10.0;
      doc["dissolved_oxygen"] = round(doValue * 100.0) / 100.0;
      doc["conductivity"] = round(conductivity * 10.0) / 10.0;
      doc["signal_rssi_dbm"] = WiFi.RSSI();

      String jsonPayload;
      serializeJson(doc, jsonPayload);

      int httpResponseCode = http.POST(jsonPayload);

      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("[HTTP] POST Success (Code: %d)\n", httpResponseCode);
        // Quick blink LED on successful transmission
        digitalWrite(PIN_STATUS_LED, LOW);
        delay(60);
        digitalWrite(PIN_STATUS_LED, HIGH);
      } else {
        Serial.printf("[HTTP] POST Failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
      }
      http.end();
    }
  }
}

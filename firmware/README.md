# AquaSense ESP32 Hardware Wiring & Sensor Guide

This document describes how to build and wire the physical IoT water monitoring node using an **ESP32** microcontroller and standard analog/digital water quality probes.

---

## 1. Bill of Materials (BOM)

| Component | Description | Interface | Approximate Cost |
| :--- | :--- | :--- | :--- |
| **ESP32 NodeMCU / WROOM-32** | Wi-Fi + Bluetooth dual-core microcontroller | Micro-USB / 3.3V | \$5.00 |
| **DFRobot Analog pH Sensor (SEN0161)** | BNC probe with signal amplifier board | Analog (0 - 3.3V) | \$18.00 |
| **DFRobot Turbidity Sensor (SEN0189)** | Optical light scattering turbidity probe | Analog (0 - 4.5V via divider) | \$12.00 |
| **DFRobot Analog TDS Sensor (SEN0244)** | Total Dissolved Solids / Conductivity meter | Analog (0 - 3.3V) | \$14.00 |
| **DS18B20 Waterproof Probe** | Stainless steel 1-Wire temperature sensor | 1-Wire Digital (4.7kΩ pullup) | \$3.50 |
| **4.7kΩ Resistor** | Pull-up resistor for DS18B20 data line | Passive | \$0.10 |
| **5V 2A Power Adapter / USB** | DC power supply | USB Type-C or 5V Pin | \$4.00 |

---

## 2. Pin Connection Diagram

```
       +---------------------------------------------+
       |                  ESP32                      |
       |                                             |
       |   [3.3V] ------+---- VCC (pH, TDS, Temp)    |
       |   [GND]  ------+---- GND (Common Ground)    |
       |   [5V]   ------+---- VCC (Turbidity board)  |
       |                                             |
       |   [GPIO 34] <------- Signal (pH Sensor)     |
       |   [GPIO 35] <------- Signal (Turbidity Div) |
       |   [GPIO 32] <------- Signal (TDS Sensor)    |
       |   [GPIO 4]  <------- Data (DS18B20 Temp)    |
       |                       |                     |
       |                       +-- [4.7kΩ] -- [3.3V] |
       +---------------------------------------------+
```

### Detailed Wiring Table

| Sensor | Sensor Pin | ESP32 Pin | Notes |
| :--- | :--- | :--- | :--- |
| **pH Sensor** | VCC | 3.3V | Requires stable power supply |
| | GND | GND | Common ground |
| | Analog Out (A) | GPIO 34 (ADC1_CH6) | ADC1 is safe to use with active Wi-Fi |
| **Turbidity Sensor** | VCC | 5V (VIN) | Turbidity emitter requires 5V |
| | GND | GND | Common ground |
| | Analog Out (A) | GPIO 35 (ADC1_CH7) | Use 1k/2k voltage divider if output > 3.3V |
| **TDS Sensor** | VCC | 3.3V | Clean 3.3V rail |
| | GND | GND | Common ground |
| | Analog Out (A) | GPIO 32 (ADC1_CH4) | Reads electrical conductivity |
| **DS18B20 Temp** | VCC (Red) | 3.3V | Digital 1-Wire bus |
| | GND (Black) | GND | Common ground |
| | Data (Yellow) | GPIO 4 | Connect 4.7kΩ resistor between Data and 3.3V |

> [!IMPORTANT]
> Always connect sensors to **ADC1** pins (GPIO 32 to 39) on the ESP32. **ADC2** cannot be used simultaneously while Wi-Fi is active on the ESP32!

---

## 3. Sensor Calibration Guide

### A. pH Sensor Calibration
1. Prepare standard pH buffer solutions (pH 4.01 and pH 7.00).
2. Clean probe tip thoroughly with distilled water and dry gently.
3. Submerge probe in **pH 7.00** solution. Read voltage output.
4. Adjust `pH_offset` in `esp32_water_monitor.ino` until the serial monitor outputs exactly `7.00`.
5. Verify in **pH 4.01** solution.

### B. TDS / Conductivity Calibration
1. Prepare standard conductivity buffer (e.g., 1413 µS/cm equivalent to ~707 ppm TDS).
2. Place TDS probe in solution with temperature probe nearby.
3. Adjust `tds_calibration_factor` so that reading equals known standard.

### C. Turbidity Sensor Calibration
1. Place sensor optical head in clean distilled water (0 NTU).
2. Voltage should measure around 4.1V - 4.2V.
3. Adjust onboard sensitivity potentiometer on the sensor adapter board until reference clear reading is achieved.

---

## 4. Flashing the ESP32
1. Install **Arduino IDE** (or VS Code + PlatformIO).
2. Add ESP32 board manager URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Install required libraries via Library Manager:
   - `ArduinoJson` (by Benoit Blanchon)
   - `OneWire` (by Paul Stoffregen)
   - `DallasTemperature` (by Miles Burton)
4. Open `firmware/esp32_water_monitor.ino`.
5. Update `WIFI_SSID`, `WIFI_PASSWORD`, and `SERVER_URL` (IP of your computer running the FastAPI server).
6. Select board **ESP32 Dev Module** and upload.

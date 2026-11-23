"""
IoT Water Quality Multi-Sensor Simulator.
Simulates realistic analog probe telemetry with sensor drift, noise, and environmental scenarios.
Can run standalone or be embedded inside the FastAPI server.
"""

import time
import math
import random
import requests
from typing import Dict, Any, Generator

SCENARIOS = {
    "clean_spring": {
        "name": "Pristine Mountain Spring",
        "description": "Natural spring water with balanced minerals and high dissolved oxygen.",
        "base": {
            "ph": 7.45,
            "turbidity": 0.45,
            "tds": 115.0,
            "temperature": 14.2,
            "dissolved_oxygen": 9.4,
            "conductivity": 180.0
        },
        "noise": {
            "ph": 0.05, "turbidity": 0.08, "tds": 5.0,
            "temperature": 0.2, "dissolved_oxygen": 0.15, "conductivity": 8.0
        }
    },
    "municipal_tap": {
        "name": "Municipal Treated Tap Water",
        "description": "Standard municipal potable supply compliant with EPA/WHO parameters.",
        "base": {
            "ph": 7.20,
            "turbidity": 1.15,
            "tds": 230.0,
            "temperature": 19.5,
            "dissolved_oxygen": 7.9,
            "conductivity": 355.0
        },
        "noise": {
            "ph": 0.08, "turbidity": 0.15, "tds": 10.0,
            "temperature": 0.3, "dissolved_oxygen": 0.2, "conductivity": 15.0
        }
    },
    "acid_rain": {
        "name": "Acid Rain & Heavy Metal Leaching",
        "description": "Severe atmospheric acid precipitation and corrosion from aged iron/lead piping.",
        "base": {
            "ph": 4.35,
            "turbidity": 3.60,
            "tds": 420.0,
            "temperature": 20.8,
            "dissolved_oxygen": 6.4,
            "conductivity": 710.0
        },
        "noise": {
            "ph": 0.12, "turbidity": 0.35, "tds": 15.0,
            "temperature": 0.4, "dissolved_oxygen": 0.25, "conductivity": 25.0
        }
    },
    "agricultural_runoff": {
        "name": "Agricultural / Fertilizer Runoff",
        "description": "High particulate turbidity, nitrates, suspended solids, and developing eutrophication.",
        "base": {
            "ph": 8.40,
            "turbidity": 16.5,
            "tds": 690.0,
            "temperature": 25.5,
            "dissolved_oxygen": 3.9,
            "conductivity": 1080.0
        },
        "noise": {
            "ph": 0.15, "turbidity": 1.2, "tds": 25.0,
            "temperature": 0.5, "dissolved_oxygen": 0.3, "conductivity": 40.0
        }
    },
    "industrial_discharge": {
        "name": "Industrial Chemical Spill",
        "description": "Alkaline effluent, toxic heavy dissolved solids, chemical discoloration.",
        "base": {
            "ph": 10.3,
            "turbidity": 26.0,
            "tds": 1380.0,
            "temperature": 29.5,
            "dissolved_oxygen": 2.1,
            "conductivity": 2250.0
        },
        "noise": {
            "ph": 0.2, "turbidity": 1.8, "tds": 45.0,
            "temperature": 0.6, "dissolved_oxygen": 0.2, "conductivity": 80.0
        }
    },
    "stagnant_biohazard": {
        "name": "Stagnant Reservoir / Microbial Hazard",
        "description": "Anoxic stagnant pool, warm temperature, high microbial and organic matter.",
        "base": {
            "ph": 6.65,
            "turbidity": 13.5,
            "tds": 540.0,
            "temperature": 31.5,
            "dissolved_oxygen": 1.45,
            "conductivity": 840.0
        },
        "noise": {
            "ph": 0.1, "turbidity": 0.9, "tds": 20.0,
            "temperature": 0.4, "dissolved_oxygen": 0.15, "conductivity": 30.0
        }
    }
}

class IoTSensorSimulator:
    def __init__(self, device_id: str = "ESP32-AQUA-01", default_scenario: str = "municipal_tap"):
        self.device_id = device_id
        self.scenario_key = default_scenario if default_scenario in SCENARIOS else "municipal_tap"
        self.step_counter = 0
        self.anomaly_active = False
        self.anomaly_remaining_ticks = 0
        self.anomaly_type = None
        self.is_running = True
        
    def set_scenario(self, scenario_key: str) -> bool:
        if scenario_key in SCENARIOS:
            self.scenario_key = scenario_key
            return True
        return False
        
    def inject_anomaly(self, anomaly_type: str = "chemical_leak", duration_ticks: int = 15):
        """
        Injects a sudden real-time sensor anomaly (e.g. pipe rupture, acid spike, turbidity surge).
        """
        self.anomaly_active = True
        self.anomaly_type = anomaly_type
        self.anomaly_remaining_ticks = duration_ticks
        
    def generate_reading(self) -> Dict[str, Any]:
        self.step_counter += 1
        scenario = SCENARIOS[self.scenario_key]
        base = scenario["base"]
        noise = scenario["noise"]
        
        # Diurnal cyclic drift using sine wave
        drift_factor = math.sin(self.step_counter * 0.08)
        
        ph = base["ph"] + (drift_factor * 0.05) + random.gauss(0, noise["ph"])
        turbidity = base["turbidity"] + (drift_factor * 0.1) + abs(random.gauss(0, noise["turbidity"]))
        tds = base["tds"] + (drift_factor * 5.0) + random.gauss(0, noise["tds"])
        temp = base["temperature"] + (drift_factor * 0.5) + random.gauss(0, noise["temperature"])
        
        # Temp & DO inverse relationship
        do = base["dissolved_oxygen"] - (0.05 * (temp - base["temperature"])) + random.gauss(0, noise["dissolved_oxygen"])
        cond = base["conductivity"] + (drift_factor * 10.0) + random.gauss(0, noise["conductivity"])
        
        # Handle active injected anomalies
        if self.anomaly_active and self.anomaly_remaining_ticks > 0:
            self.anomaly_remaining_ticks -= 1
            if self.anomaly_type == "acid_spike":
                ph -= 3.2
                cond += 500
            elif self.anomaly_type == "turbidity_surge":
                turbidity += 30.0
                tds += 400
            elif self.anomaly_type == "thermal_pollution":
                temp += 12.0
                do -= 3.5
            else: # chemical_leak
                tds += 850
                cond += 1400
                ph += 2.8
                turbidity += 18.0
                do -= 4.0
        else:
            self.anomaly_active = False
            self.anomaly_type = None
            
        # Physical boundary clipping
        ph = round(max(0.0, min(14.0, float(ph))), 2)
        turbidity = round(max(0.05, min(100.0, float(turbidity))), 2)
        tds = round(max(10.0, min(5000.0, float(tds))), 1)
        temp = round(max(0.0, min(60.0, float(temp))), 1)
        do = round(max(0.1, min(15.0, float(do))), 2)
        cond = round(max(10.0, min(8000.0, float(cond))), 1)
        
        return {
            "device_id": self.device_id,
            "scenario": scenario["name"],
            "scenario_key": self.scenario_key,
            "ph": ph,
            "turbidity": turbidity,
            "tds": tds,
            "temperature": temp,
            "dissolved_oxygen": do,
            "conductivity": cond,
            "anomaly_active": self.anomaly_active,
            "anomaly_type": self.anomaly_type,
            "battery_percent": max(15, 100 - (self.step_counter // 100)),
            "signal_rssi_dbm": random.choice([-52, -54, -58, -61, -63])
        }

    def stream(self, interval_seconds: float = 2.0) -> Generator[Dict[str, Any], None, None]:
        while self.is_running:
            yield self.generate_reading()
            time.sleep(interval_seconds)

def run_standalone_simulator(server_url: str = "http://127.0.0.1:8000/api/telemetry", interval: float = 2.5):
    print(f"Starting IoT Sensor Simulator sending to: {server_url}")
    sim = IoTSensorSimulator()
    try:
        while True:
            reading = sim.generate_reading()
            try:
                resp = requests.post(server_url, json=reading, timeout=3.0)
                print(f"[{reading['device_id']}] POST status: {resp.status_code} | pH: {reading['ph']} | Turb: {reading['turbidity']} | TDS: {reading['tds']}")
            except Exception as e:
                print(f"Failed to post reading: {e}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Simulator stopped.")

if __name__ == '__main__':
    sim = IoTSensorSimulator()
    print("Sample telemetry reading:")
    print(sim.generate_reading())

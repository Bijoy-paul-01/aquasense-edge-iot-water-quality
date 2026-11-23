"""
Comprehensive Automated Test Suite for AquaSense System.
Tests ML Engine, Database, IoT Simulator, and FastAPI REST Endpoints.
"""

import os
import sys
from starlette.testclient import TestClient

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend.main import app
from ml.inference import get_inference_engine
from simulator.iot_sensor_simulator import IoTSensorSimulator, SCENARIOS
from backend.database import get_db_connection, save_telemetry, get_latest_telemetry

def test_ml_inference():
    print("\n--- Testing Machine Learning Inference Engine ---")
    engine = get_inference_engine()
    
    # Safe water test
    safe_sample = {
        'ph': 7.3, 'turbidity': 1.1, 'tds': 210.0,
        'temperature': 18.5, 'dissolved_oxygen': 8.5, 'conductivity': 320.0
    }
    safe_res = engine.predict(safe_sample)
    assert safe_res['is_potable'] is True
    assert safe_res['potability'] == 'SAFE'
    assert safe_res['wqi']['wqi'] >= 75.0
    print(f"Safe sample test passed: WQI = {safe_res['wqi']['wqi']}, Potability = {safe_res['potability']}")
    
    # Unsafe water test (acidic + high turbidity)
    dirty_sample = {
        'ph': 4.1, 'turbidity': 22.0, 'tds': 950.0,
        'temperature': 28.0, 'dissolved_oxygen': 2.8, 'conductivity': 1600.0
    }
    dirty_res = engine.predict(dirty_sample)
    assert dirty_res['is_potable'] is False
    assert dirty_res['potability'] == 'UNSAFE'
    assert dirty_res['wqi']['wqi'] < 50.0
    assert dirty_res['diagnostics']['has_critical'] is True
    print(f"Unsafe sample test passed: WQI = {dirty_res['wqi']['wqi']}, Potability = {dirty_res['potability']}, Breaches = {dirty_res['diagnostics']['breach_count']}")

def test_iot_simulator():
    print("\n--- Testing IoT Multi-Sensor Simulator ---")
    sim = IoTSensorSimulator(device_id="TEST-NODE-01")
    reading = sim.generate_reading()
    assert reading['device_id'] == "TEST-NODE-01"
    assert 0.0 <= reading['ph'] <= 14.0
    assert reading['turbidity'] >= 0.0
    assert reading['tds'] > 0.0
    print(f"Simulator generated valid reading: pH={reading['ph']}, Turb={reading['turbidity']}, TDS={reading['tds']}")
    
    # Test scenario change
    assert sim.set_scenario("acid_rain") is True
    acid_reading = sim.generate_reading()
    assert acid_reading['ph'] < 6.0
    print(f"Acid rain scenario successfully produced low pH: {acid_reading['ph']}")

def test_fastapi_endpoints():
    print("\n--- Testing FastAPI Endpoints via TestClient ---")
    client = TestClient(app)
    
    # 1. Root dashboard
    res = client.get("/")
    assert res.status_code == 200
    assert "AquaSense" in res.text
    print("GET / -> 200 OK (Dashboard HTML loaded)")
    
    # 2. Simulator status
    res = client.get("/api/simulator/status")
    assert res.status_code == 200
    data = res.json()
    assert "available_scenarios" in data
    print("GET /api/simulator/status -> 200 OK")
    
    # 3. Post Telemetry
    sample_payload = {
        "device_id": "TEST-PROBE",
        "scenario": "Unit Test",
        "ph": 7.4,
        "turbidity": 1.2,
        "tds": 220.0,
        "temperature": 19.0,
        "dissolved_oxygen": 8.0,
        "conductivity": 340.0
    }
    res = client.post("/api/telemetry", json=sample_payload)
    assert res.status_code == 200
    telemetry_resp = res.json()
    assert telemetry_resp['inference']['is_potable'] is True
    print(f"POST /api/telemetry -> 200 OK (Inference: {telemetry_resp['inference']['potability']})")
    
    # 4. Predict endpoint (Lab Calculator)
    res = client.post("/api/predict", json={
        "ph": 5.2, "turbidity": 15.0, "tds": 800.0,
        "temperature": 25.0, "dissolved_oxygen": 3.0, "conductivity": 1200.0
    })
    assert res.status_code == 200
    pred = res.json()
    assert pred['is_potable'] is False
    print("POST /api/predict -> 200 OK (Handled custom water sample)")
    
    # 5. Get history & stats
    res_hist = client.get("/api/telemetry/history?limit=10")
    assert res_hist.status_code == 200
    assert "history" in res_hist.json()
    
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    print("GET /api/stats -> 200 OK")

    # 6. Test Conference Paper PDF endpoint
    res_pdf = client.get("/paper/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    print(f"GET /paper/pdf -> 200 OK (Serving {len(res_pdf.content)} bytes PDF)")

if __name__ == '__main__':
    test_ml_inference()
    test_iot_simulator()
    test_fastapi_endpoints()
    print("\n[SUCCESS] All system tests passed with 100% success!")

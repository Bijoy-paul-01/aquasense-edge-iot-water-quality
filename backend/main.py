"""
FastAPI Server for AquaSense IoT & ML Water Quality Detection System.
Provides REST APIs, WebSocket streaming, background IoT simulation, and ML inference.
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ml.inference import get_inference_engine
from backend.database import (
    save_telemetry, get_latest_telemetry, get_telemetry_history,
    get_alerts, acknowledge_alert, acknowledge_all_alerts, get_summary_stats
)
from simulator.iot_sensor_simulator import IoTSensorSimulator, SCENARIOS

app = FastAPI(
    title="AquaSense IoT & ML Water Quality Detection System",
    description="Real-time water quality monitoring, WQI computation, and ML-powered potability prediction.",
    version="2.0.0"
)

# Enable CORS for flexible dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(BASE_DIR, 'static')
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize ML inference engine
inference_engine = get_inference_engine()

# Global IoT simulator instance
iot_simulator = IoTSensorSimulator(device_id="ESP32-AQUA-01", default_scenario="municipal_tap")
simulator_task: Optional[asyncio.Task] = None
simulator_interval_seconds = 2.0


# ---------------- WEBSOCKET CONNECTION MANAGER ----------------
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

ws_manager = WebSocketManager()


# ---------------- PYDANTIC MODELS ----------------
class TelemetryInput(BaseModel):
    device_id: Optional[str] = "ESP32-NODE-01"
    scenario: Optional[str] = "Live Hardware"
    ph: float = Field(..., ge=0.0, le=14.0, description="pH level (0-14)")
    turbidity: float = Field(..., ge=0.0, le=100.0, description="Turbidity in NTU")
    tds: float = Field(..., ge=0.0, le=5000.0, description="Total Dissolved Solids in ppm")
    temperature: float = Field(..., ge=-10.0, le=70.0, description="Temperature in °C")
    dissolved_oxygen: float = Field(..., ge=0.0, le=20.0, description="Dissolved Oxygen in mg/L")
    conductivity: float = Field(..., ge=0.0, le=10000.0, description="Conductivity in µS/cm")
    signal_rssi_dbm: Optional[int] = -60
    battery_percent: Optional[int] = 100

class ManualPredictionInput(BaseModel):
    ph: float
    turbidity: float
    tds: float
    temperature: float
    dissolved_oxygen: float
    conductivity: float

class ScenarioChangeRequest(BaseModel):
    scenario_key: str

class AnomalyRequest(BaseModel):
    anomaly_type: str = "chemical_leak"
    duration_ticks: int = 12


# ---------------- REST ENDPOINTS ----------------
@app.get("/")
async def serve_dashboard():
    index_file = os.path.join(static_dir, 'index.html')
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AquaSense API is running. Dashboard HTML not found."}

@app.get("/paper/pdf")
async def download_conference_paper():
    """
    Downloads or views the compiled IEEE Conference Paper PDF.
    """
    pdf_path = os.path.join(BASE_DIR, 'paper', 'AquaSense_IEEE_Conference_Paper.pdf')
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename="AquaSense_IEEE_Conference_Paper.pdf")
    raise HTTPException(status_code=404, detail="Conference paper PDF not found.")

@app.post("/api/telemetry")
async def ingest_telemetry(data: TelemetryInput):
    """
    Ingests sensor reading, runs ML inference, logs to DB, and broadcasts live to WebSocket clients.
    """
    data_dict = data.dict()
    data_dict["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Run ML inference & WQI calculation
    inference_result = inference_engine.predict(data_dict)
    
    # Persist in SQLite
    telemetry_id = save_telemetry(data_dict, inference_result)
    
    # Pack broadcast payload
    broadcast_payload = {
        "event": "telemetry_update",
        "telemetry_id": telemetry_id,
        "timestamp": data_dict["timestamp"],
        "device_id": data_dict["device_id"],
        "scenario": data_dict["scenario"],
        "telemetry": {
            "ph": data_dict["ph"],
            "turbidity": data_dict["turbidity"],
            "tds": data_dict["tds"],
            "temperature": data_dict["temperature"],
            "dissolved_oxygen": data_dict["dissolved_oxygen"],
            "conductivity": data_dict["conductivity"],
            "battery_percent": data_dict.get("battery_percent", 100),
            "signal_rssi_dbm": data_dict.get("signal_rssi_dbm", -60)
        },
        "inference": inference_result
    }
    
    # Broadcast to all connected WebSockets
    await ws_manager.broadcast(broadcast_payload)
    return broadcast_payload

@app.get("/api/telemetry/latest")
async def get_latest():
    latest = get_latest_telemetry()
    if not latest:
        return {"status": "empty", "message": "No telemetry readings recorded yet."}
    return latest

@app.get("/api/telemetry/history")
async def get_history(limit: int = Query(60, ge=10, le=500)):
    history = get_telemetry_history(limit=limit)
    return {"count": len(history), "history": history}

@app.post("/api/predict")
async def predict_sample(sample: ManualPredictionInput):
    """
    Run ad-hoc ML model prediction and WQI analysis on custom parameters.
    """
    result = inference_engine.predict(sample.dict())
    return result

@app.get("/api/alerts")
async def list_alerts(limit: int = 50, unacknowledged_only: bool = False):
    alerts = get_alerts(limit=limit, only_unacked=unacknowledged_only)
    return {"alerts": alerts, "count": len(alerts)}

@app.post("/api/alerts/{alert_id}/ack")
async def acknowledge_single_alert(alert_id: int):
    success = acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "alert_id": alert_id}

@app.post("/api/alerts/ack-all")
async def acknowledge_all():
    count = acknowledge_all_alerts()
    return {"status": "success", "acknowledged_count": count}

@app.get("/api/stats")
async def get_stats():
    return get_summary_stats()

@app.get("/api/model/info")
async def get_model_info():
    return inference_engine.metadata

@app.get("/api/simulator/status")
async def get_simulator_status():
    return {
        "is_running": iot_simulator.is_running,
        "scenario_key": iot_simulator.scenario_key,
        "scenario_name": SCENARIOS[iot_simulator.scenario_key]["name"],
        "description": SCENARIOS[iot_simulator.scenario_key]["description"],
        "anomaly_active": iot_simulator.anomaly_active,
        "anomaly_type": iot_simulator.anomaly_type,
        "available_scenarios": [
            {"key": k, "name": v["name"], "description": v["description"]}
            for k, v in SCENARIOS.items()
        ]
    }

@app.post("/api/simulator/scenario")
async def set_simulator_scenario(req: ScenarioChangeRequest):
    success = iot_simulator.set_scenario(req.scenario_key)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {req.scenario_key}")
    return {
        "status": "success",
        "scenario_key": req.scenario_key,
        "scenario_name": SCENARIOS[req.scenario_key]["name"]
    }

@app.post("/api/simulator/toggle")
async def toggle_simulator():
    iot_simulator.is_running = not iot_simulator.is_running
    return {"is_running": iot_simulator.is_running}

@app.post("/api/simulator/anomaly")
async def trigger_simulator_anomaly(req: AnomalyRequest):
    iot_simulator.inject_anomaly(req.anomaly_type, req.duration_ticks)
    return {
        "status": "anomaly_injected",
        "type": req.anomaly_type,
        "duration_ticks": req.duration_ticks
    }


# ---------------- WEBSOCKET ENDPOINT ----------------
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    # Send initial greeting & latest data
    try:
        latest = get_latest_telemetry()
        stats = get_summary_stats()
        await websocket.send_text(json.dumps({
            "event": "connected",
            "message": "Connected to AquaSense IoT & ML Real-time stream",
            "latest": latest,
            "stats": stats,
            "simulator": {
                "scenario": iot_simulator.scenario_key,
                "is_running": iot_simulator.is_running
            }
        }))
        
        while True:
            # Keep socket open and accept incoming client messages if any
            client_msg = await websocket.receive_text()
            try:
                data = json.loads(client_msg)
                if data.get("action") == "change_scenario":
                    iot_simulator.set_scenario(data.get("scenario_key", "municipal_tap"))
                elif data.get("action") == "inject_anomaly":
                    iot_simulator.inject_anomaly(data.get("anomaly_type", "chemical_leak"))
                elif data.get("action") == "toggle_stream":
                    iot_simulator.is_running = not iot_simulator.is_running
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# ---------------- BACKGROUND IOT SIMULATION TASK ----------------
async def background_iot_loop():
    """
    Internal background task that feeds the pipeline with continuous sensor telemetry.
    Allows out-of-the-box operation even if external hardware is not actively connected.
    """
    print("[Simulator] Background IoT simulation task started.")
    while True:
        try:
            if iot_simulator.is_running:
                reading = iot_simulator.generate_reading()
                telemetry_model = TelemetryInput(**reading)
                await ingest_telemetry(telemetry_model)
        except Exception as e:
            print(f"[Simulator] Error in background simulator loop: {e}")
        await asyncio.sleep(simulator_interval_seconds)

@app.on_event("startup")
async def startup_event():
    global simulator_task
    simulator_task = asyncio.create_task(background_iot_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global simulator_task
    if simulator_task:
        simulator_task.cancel()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

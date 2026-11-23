"""
AquaSense IoT & ML Water Quality Detection System - Master Runner
Starts the entire system (ML models, backend, IoT simulator, and dashboard) in one command.
"""

import os
import sys
import webbrowser
import threading
import time

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    sys.path.insert(0, base_dir)

    print("=" * 68)
    print("  *** AQUASENSE - IoT & Machine Learning Water Quality System ***")
    print("=" * 68)

    # 1. Check ML Model existence
    model_path = os.path.join(base_dir, 'ml', 'models', 'potability_classifier.joblib')
    if not os.path.exists(model_path):
        print("\n[ML] Model artifacts not found. Starting automatic training pipeline...")
        from ml.train import train_and_export_models
        train_and_export_models()
    else:
        print("\n[ML] Pre-trained Potability & WQI models verified.")

    # 2. Check Database existence
    from backend.database import init_db
    init_db()
    print("[DB] SQLite telemetry database initialized.")

    # 3. Auto-open browser after 1.5 seconds
    def open_browser():
        time.sleep(1.5)
        url = "http://127.0.0.1:8000"
        print(f"\n[Browser] Launching interactive dashboard at: {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 4. Start Uvicorn Server
    print("\n[Server] Starting FastAPI server on http://127.0.0.1:8000...")
    print("[Simulator] Embedded IoT Multi-Sensor Stream active (Cadence: 2.0s)")
    print("[WebSocket] Real-time stream available at ws://127.0.0.1:8000/ws/live")
    print("\nPress Ctrl+C to terminate the server.\n")

    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")

if __name__ == '__main__':
    main()

"""
Database management for water quality telemetry, inference history, and alerts using SQLite.
"""

import os
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'water_quality.db')

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Telemetry & Inference log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        device_id TEXT NOT NULL,
        scenario TEXT,
        ph REAL NOT NULL,
        turbidity REAL NOT NULL,
        tds REAL NOT NULL,
        temperature REAL NOT NULL,
        dissolved_oxygen REAL NOT NULL,
        conductivity REAL NOT NULL,
        potability TEXT NOT NULL,
        is_potable INTEGER NOT NULL,
        confidence REAL NOT NULL,
        wqi REAL NOT NULL,
        wqi_category TEXT NOT NULL
    );
    """)
    
    # Alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        device_id TEXT NOT NULL,
        severity TEXT NOT NULL,
        parameter TEXT NOT NULL,
        value TEXT NOT NULL,
        message TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);")
    
    conn.commit()
    conn.close()

def save_telemetry(data: Dict[str, Any], inference: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_iso = data.get('timestamp') or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    device_id = data.get('device_id', 'ESP32-NODE-01')
    scenario = data.get('scenario', 'Normal Tap Water')
    
    features = inference.get('features', {})
    wqi_info = inference.get('wqi', {})
    
    cursor.execute("""
    INSERT INTO telemetry (
        timestamp, device_id, scenario, ph, turbidity, tds,
        temperature, dissolved_oxygen, conductivity,
        potability, is_potable, confidence, wqi, wqi_category
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_iso,
        device_id,
        scenario,
        features.get('ph', data.get('ph', 7.0)),
        features.get('turbidity', data.get('turbidity', 1.0)),
        features.get('tds', data.get('tds', 200.0)),
        features.get('temperature', data.get('temperature', 20.0)),
        features.get('dissolved_oxygen', data.get('dissolved_oxygen', 8.0)),
        features.get('conductivity', data.get('conductivity', 350.0)),
        inference.get('potability', 'SAFE'),
        1 if inference.get('is_potable', True) else 0,
        inference.get('confidence', 95.0),
        wqi_info.get('wqi', 85.0),
        wqi_info.get('category', 'Excellent')
    ))
    
    telemetry_id = cursor.lastrowid
    
    # Check for alerts to record
    diagnostics = inference.get('diagnostics', {})
    breaches = diagnostics.get('breaches', [])
    for b in breaches:
        # Only record CRITICAL and WARNING alerts in the persistent table
        if b.get('severity') in ['CRITICAL', 'WARNING']:
            cursor.execute("""
            INSERT INTO alerts (
                timestamp, device_id, severity, parameter, value, message, acknowledged
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                now_iso,
                device_id,
                b['severity'],
                b['parameter'],
                str(b['value']),
                b['issue']
            ))
            
    conn.commit()
    conn.close()
    return telemetry_id

def get_latest_telemetry() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM telemetry ORDER BY id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_telemetry_history(limit: int = 60) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM (
        SELECT * FROM telemetry ORDER BY id DESC LIMIT ?
    ) ORDER BY id ASC
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_alerts(limit: int = 50, only_unacked: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if only_unacked:
        cursor.execute("SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY id DESC LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def acknowledge_alert(alert_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def acknowledge_all_alerts() -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE acknowledged = 0")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def get_summary_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), AVG(wqi), SUM(is_potable) FROM telemetry")
    total_count, avg_wqi, total_potable = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
    active_alerts = cursor.fetchone()[0]
    
    conn.close()
    
    total_count = total_count or 0
    avg_wqi = round(avg_wqi, 1) if avg_wqi else 0.0
    safe_rate = round((total_potable / total_count * 100), 1) if total_count > 0 and total_potable else 0.0
    
    return {
        "total_readings": total_count,
        "avg_wqi": avg_wqi,
        "safe_percentage": safe_rate,
        "active_alerts": active_alerts
    }

# Initialize tables
init_db()

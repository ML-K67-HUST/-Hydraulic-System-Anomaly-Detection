#!/usr/bin/env python3
"""
Create Clean Grafana Dashboard for Raw Sensor Data
"""

import requests
import json
import time

import os

# Configuration from Environment Variables or Defaults
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASS", "admin")

def create_dashboard():
    session = requests.Session()
    session.auth = (GRAFANA_USER, GRAFANA_PASS)
    
    print("=" * 80)
    print("🎨 Creating 'Hydraulic System - Raw Data' Dashboard")
    print("=" * 80)
    
    # Dashboard definition
    dashboard = {
        "dashboard": {
            "title": "Hydraulic System - Raw Sensor Data",
            "tags": ["raw", "monitoring", "hydraulic"],
            "timezone": "browser",
            "refresh": "5s",
            "panels": [
                # --- ROW 1: PRESSURE ---
                {
                    "id": 1,
                    "title": "Pressure Sensors (PS1-PS6)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_raw_ps1', "legendFormat": "PS1"},
                        {"refId": "B", "expr": 'hydraulic_raw_ps2', "legendFormat": "PS2"},
                        {"refId": "C", "expr": 'hydraulic_raw_ps3', "legendFormat": "PS3"},
                        {"refId": "D", "expr": 'hydraulic_raw_ps4', "legendFormat": "PS4"},
                        {"refId": "E", "expr": 'hydraulic_raw_ps5', "legendFormat": "PS5"},
                        {"refId": "F", "expr": 'hydraulic_raw_ps6', "legendFormat": "PS6"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "bar", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                 # --- ROW 2: TEMPERATURE ---
                {
                    "id": 2,
                    "title": "Temperature Sensors (TS1-TS4)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 8, "w": 24, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_raw_ts1', "legendFormat": "TS1"},
                        {"refId": "B", "expr": 'hydraulic_raw_ts2', "legendFormat": "TS2"},
                        {"refId": "C", "expr": 'hydraulic_raw_ts3', "legendFormat": "TS3"},
                        {"refId": "D", "expr": 'hydraulic_raw_ts4', "legendFormat": "TS4"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "celsius", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                # --- ROW 3: FLOW & MOTOR ---
                {
                    "id": 3,
                    "title": "Flow Rate (FS1, FS2)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 16, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_raw_fs1', "legendFormat": "FS1"},
                        {"refId": "B", "expr": 'hydraulic_raw_fs2', "legendFormat": "FS2"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "l/min", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                {
                    "id": 4,
                    "title": "Motor Power (EPS1)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 16, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_raw_eps1', "legendFormat": "EPS1"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "watt", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                }
            ]
        },
        "overwrite": True
    }

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # POST to Grafana
    try:
        resp = session.post(f"{GRAFANA_URL}/api/dashboards/db", data=json.dumps(dashboard), headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print("\n✅ Dashboard created successfully!")
            print(f"🔗 {GRAFANA_URL}{data['url']}")
        else:
            print(f"\n❌ Failed to create dashboard: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"\n❌ Error connecting to Grafana: {e}")

if __name__ == "__main__":
    create_dashboard()

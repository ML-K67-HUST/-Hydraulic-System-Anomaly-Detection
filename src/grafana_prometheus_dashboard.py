#!/usr/bin/env python3
"""
Create Clean Grafana Dashboard for Raw Sensor Data (Replaces Legacy Dashboard)
"""

import requests
import json
import time

GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASS = "admin"

def create_dashboard():
    session = requests.Session()
    session.auth = (GRAFANA_USER, GRAFANA_PASS)
    
    print("=" * 80)
    print("🎨 Updating 'Hydraulic System - Prometheus' (Legacy) to Clean Raw Data")
    print("=" * 80)
    
    # Dashboard definition
    dashboard = {
        "dashboard": {
            "title": "Hydraulic System - Prometheus (Raw Data - CLEAN)",
            "uid": "hydraulic-system-prometheus", # Preserve UID to overwrite existing
            "tags": ["raw", "monitoring", "hydraulic", "clean"],
            "timezone": "browser",
            "refresh": "5s",
            "time": {"from": "now-5m", "to": "now"},
            "graphTooltip": 1, # Shared Crosshair (Critical for correlation)
            "panels": [
                # --- ROW 0: KAFKA CONSUMER HEALTH ---
                {
                    "id": 20,
                    "title": "📥 Message Rate (Msg/sec)",
                    "type": "stat",
                    "gridPos": {"x": 0, "y": 0, "w": 4, "h": 4},
                    "targets": [{"refId": "A", "expr": "rate(hydraulic_messages_total[1m])", "legendFormat": "Speed"}],
                     "fieldConfig": {
                        "defaults": {
                            "displayName": "Speed",
                            "unit": "pps", 
                            "color": {"mode": "thresholds"},
                            "thresholds": {"mode": "absolute", "steps": [{"value": 0, "color": "red"}, {"value": 1, "color": "green"}]}
                        }
                    }
                },
                {
                    "id": 21,
                    "title": "📦 Total Messages Processed",
                    "type": "stat",
                    "gridPos": {"x": 4, "y": 0, "w": 4, "h": 4},
                    "targets": [{"refId": "A", "expr": "hydraulic_messages_total", "legendFormat": "Total"}],
                     "fieldConfig": {"defaults": {"displayName": "Total", "unit": "none", "color": {"mode": "fixed", "fixedColor": "blue"}}}
                },
                {
                    "id": 22,
                    "title": "⏱️ Consumer Latency",
                    "type": "stat",
                    "gridPos": {"x": 8, "y": 0, "w": 4, "h": 4},
                    "targets": [{"refId": "A", "expr": "time() - hydraulic_last_update_timestamp", "legendFormat": "Lag"}],
                     "fieldConfig": {
                        "defaults": {
                            "displayName": "Lag",
                            "unit": "s",
                            "thresholds": {"mode": "absolute", "steps": [{"value": 0, "color": "green"}, {"value": 5, "color": "orange"}, {"value": 30, "color": "red"}]}
                        }
                    }
                },
                # --- ROW 1: REAL-TIME VITALS (GAUGES) ---
                {
                    "id": 10,
                    "title": "🧭 Main System Vitals",
                    "type": "gauge",
                    "gridPos": {"x": 0, "y": 4, "w": 8, "h": 6},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_ps1_value_clean', "legendFormat": "Pressure (PS1)"},
                        {"refId": "B", "expr": 'hydraulic_ts1_value_clean', "legendFormat": "Temp (TS1)"},
                        {"refId": "C", "expr": 'hydraulic_fs1_value_clean', "legendFormat": "Flow (FS1)"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "displayName": "${__field.labels}",
                            "min": 0,
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "green"},
                                    {"value": 150, "color": "orange"},
                                    {"value": 180, "color": "red"}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 11,
                    "title": "⚡ Motor Power (EPS1)",
                    "type": "stat",
                    "gridPos": {"x": 8, "y": 0, "w": 4, "h": 6},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_eps1_value_clean', "legendFormat": "Power"}
                    ],
                    "options": {
                        "colorMode": "background",
                        "graphMode": "area"
                    },
                    "fieldConfig": {"defaults": {"unit": "watt"}}
                },
                 {
                    "id": 12,
                    "title": "🌡️ Temperature Overview (Bar Gauge)",
                    "type": "bargauge",
                    "gridPos": {"x": 12, "y": 0, "w": 12, "h": 6},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_ts1_value_clean', "legendFormat": "TS1"},
                        {"refId": "B", "expr": 'hydraulic_ts2_value_clean', "legendFormat": "TS2"},
                        {"refId": "C", "expr": 'hydraulic_ts3_value_clean', "legendFormat": "TS3"},
                        {"refId": "D", "expr": 'hydraulic_ts4_value_clean', "legendFormat": "TS4"}
                    ],
                    "options": {
                        "orientation": "vertical",
                        "displayMode": "lcd",
                        "showUnfilled": True
                    },
                     "fieldConfig": {"defaults": {"unit": "celsius", "min": 0, "max": 100, "color": {"mode": "continuous-GrYlRd"}}}
                },

                # --- ROW 2: PRESSURE ANALYSIS ---
                {
                    "id": 1,
                    "title": "Pressure Sensors (PS1-PS6) - Time Series",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 6, "w": 24, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_ps1_value_clean', "legendFormat": "PS1"},
                        {"refId": "B", "expr": 'hydraulic_ps2_value_clean', "legendFormat": "PS2"},
                        {"refId": "C", "expr": 'hydraulic_ps3_value_clean', "legendFormat": "PS3"},
                        {"refId": "D", "expr": 'hydraulic_ps4_value_clean', "legendFormat": "PS4"},
                        {"refId": "E", "expr": 'hydraulic_ps5_value_clean', "legendFormat": "PS5"},
                        {"refId": "F", "expr": 'hydraulic_ps6_value_clean', "legendFormat": "PS6"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "bar", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                
                # --- ROW 3: PRESSURE HEATMAPS (DISTRIBUTION) ---
                {
                    "id": 13, "title": "🔥 PS1 Distribution", "type": "heatmap",
                    "gridPos": {"x": 0, "y": 14, "w": 6, "h": 6},
                    "targets": [{"refId": "A", "expr": 'hydraulic_ps1_value_clean', "format": "heatmap"}],
                    "options": {"calculate": True, "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}}
                },
                {
                    "id": 14, "title": "🔥 PS2 Distribution", "type": "heatmap",
                    "gridPos": {"x": 6, "y": 14, "w": 6, "h": 6},
                    "targets": [{"refId": "A", "expr": 'hydraulic_ps2_value_clean', "format": "heatmap"}],
                    "options": {"calculate": True, "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}}
                },
                {
                    "id": 15, "title": "🔥 PS3 Distribution", "type": "heatmap",
                    "gridPos": {"x": 12, "y": 14, "w": 6, "h": 6},
                    "targets": [{"refId": "A", "expr": 'hydraulic_ps3_value_clean', "format": "heatmap"}],
                    "options": {"calculate": True, "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}}
                },
                {
                    "id": 16, "title": "🔥 PS4 Distribution", "type": "heatmap",
                    "gridPos": {"x": 18, "y": 14, "w": 6, "h": 6},
                    "targets": [{"refId": "A", "expr": 'hydraulic_ps4_value_clean', "format": "heatmap"}],
                    "options": {"calculate": True, "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}}
                },

                 # --- ROW 4: TEMPERATURE & VIBRATION ---
                {
                    "id": 2,
                    "title": "Temperature Sensors (TS1-TS4)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 20, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_ts1_value_clean', "legendFormat": "TS1"},
                        {"refId": "B", "expr": 'hydraulic_ts2_value_clean', "legendFormat": "TS2"},
                        {"refId": "C", "expr": 'hydraulic_ts3_value_clean', "legendFormat": "TS3"},
                        {"refId": "D", "expr": 'hydraulic_ts4_value_clean', "legendFormat": "TS4"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "celsius", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                {
                    "id": 5,
                    "title": "Vibration (VS1) & Cooling Efficiency",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 20, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_vs1_value_clean', "legendFormat": "Vibration (VS1)"},
                        {"refId": "B", "expr": 'hydraulic_ce_value_clean', "legendFormat": "Cooling Eff (CE)"},
                        {"refId": "C", "expr": 'hydraulic_cp_value_clean', "legendFormat": "Cooling Power (CP)"},
                        {"refId": "D", "expr": 'hydraulic_se_value_clean', "legendFormat": "Efficiency (SE)"}
                    ],
                     "fieldConfig": {"defaults": {"custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                
                # --- ROW 5: FLOW & MOTOR ---

                # --- ROW 3: FLOW & MOTOR ---
                {
                    "id": 3,
                    "title": "Flow Rate (FS1, FS2)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 28, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_fs1_value_clean', "legendFormat": "FS1"},
                        {"refId": "B", "expr": 'hydraulic_fs2_value_clean', "legendFormat": "FS2"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "l/min", "custom": {"drawStyle": "line", "lineWidth": 1}}}
                },
                {
                    "id": 4,
                    "title": "Motor Power Trend (EPS1)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 28, "w": 12, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_eps1_value_clean', "legendFormat": "EPS1"}
                    ],
                    "fieldConfig": {"defaults": {"unit": "watt", "custom": {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 10}}}
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
            print("\n✅ Dashboard updated successfully!")
            print(f"🔗 {GRAFANA_URL}{data['url']}")
        else:
            print(f"\n❌ Failed to create dashboard: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"\n❌ Error connecting to Grafana: {e}")

if __name__ == "__main__":
    create_dashboard()

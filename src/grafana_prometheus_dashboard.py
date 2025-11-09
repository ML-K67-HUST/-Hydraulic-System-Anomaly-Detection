#!/usr/bin/env python3
"""
Create Grafana Dashboard for Prometheus datasource
Much simpler than MongoDB!
"""

import requests
import json

GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASS = "admin"

def create_dashboard():
    session = requests.Session()
    session.auth = (GRAFANA_USER, GRAFANA_PASS)
    
    print("=" * 80)
    print("🎯 Creating Prometheus-based Dashboard")
    print("=" * 80)
    
    # Dashboard with Prometheus queries
    dashboard = {
        "dashboard": {
            "title": "Hydraulic System - Prometheus",
            "tags": ["hydraulic", "prometheus", "realtime"],
            "timezone": "browser",
            "refresh": "5s",
            "panels": [
                # Panel 1: Total Messages
                {
                    "id": 1,
                    "title": "📊 Total Messages Processed",
                    "type": "stat",
                    "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "hydraulic_messages_total",
                        "legendFormat": "Total Messages"
                    }],
                    "options": {
                        "textMode": "value_and_name",
                        "colorMode": "value",
                        "graphMode": "area"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 1000, "color": "yellow"},
                                    {"value": 10000, "color": "green"}
                                ]
                            }
                        }
                    }
                },
                # Panel 2: Messages Rate
                {
                    "id": 2,
                    "title": "⚡ Message Rate (per second)",
                    "type": "stat",
                    "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "rate(hydraulic_messages_total[1m])",
                        "legendFormat": "Messages/sec"
                    }],
                    "options": {
                        "textMode": "value_and_name",
                        "colorMode": "value",
                        "graphMode": "area"
                    }
                },
                # Panel 3: PS1 Pressure (Graph)
                {
                    "id": 3,
                    "title": "📈 PS1 - Pressure Sensor 1",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
                    "targets": [{
                        "refId": "A",
                        "expr": 'hydraulic_ps1_value{sensor="PS1"}',
                        "legendFormat": "PS1 Pressure"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "fillOpacity": 10
                            },
                            "unit": "bar"
                        }
                    }
                },
                # Panel 4: EPS1 Motor Power (Graph)
                {
                    "id": 4,
                    "title": "⚡ EPS1 - Motor Power",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8},
                    "targets": [{
                        "refId": "A",
                        "expr": 'hydraulic_eps1_value{sensor="EPS1"}',
                        "legendFormat": "Motor Power (W)"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "fillOpacity": 10
                            },
                            "unit": "watt"
                        }
                    }
                },
                # Panel 5: All Pressure Sensors (PS1-6)
                {
                    "id": 5,
                    "title": "🔵 All Pressure Sensors (PS1-PS6)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 12, "w": 24, "h": 10},
                    "targets": [
                        {
                            "refId": f"PS{i}",
                            "expr": f'hydraulic_ps{i}_value{{sensor="PS{i}"}}',
                            "legendFormat": f"PS{i}"
                        } for i in range(1, 7)
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            },
                            "unit": "bar"
                        }
                    }
                },
                # Panel 6: Temperature Sensors (TS1-4)
                {
                    "id": 6,
                    "title": "🌡️ Temperature Sensors (TS1-TS4)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 22, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": f"TS{i}",
                            "expr": f'hydraulic_ts{i}_value{{sensor="TS{i}"}}',
                            "legendFormat": f"TS{i}"
                        } for i in range(1, 5)
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            },
                            "unit": "celsius"
                        }
                    }
                },
                # Panel 7: Flow Sensors (FS1-2)
                {
                    "id": 7,
                    "title": "💧 Volume Flow Sensors",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 22, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "FS1",
                            "expr": 'hydraulic_fs1_value{sensor="FS1"}',
                            "legendFormat": "FS1"
                        },
                        {
                            "refId": "FS2",
                            "expr": 'hydraulic_fs2_value{sensor="FS2"}',
                            "legendFormat": "FS2"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth"
                            },
                            "unit": "velocityms"
                        }
                    }
                },
                # Panel 8: Sample Counts per Sensor
                {
                    "id": 8,
                    "title": "📦 Samples Received per Sensor",
                    "type": "bargauge",
                    "gridPos": {"x": 12, "y": 0, "w": 12, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": 'hydraulic_ps1_samples_total',
                        "legendFormat": "{{sensor}}"
                    }],
                    "options": {
                        "orientation": "horizontal",
                        "displayMode": "gradient"
                    }
                }
            ]
        },
        "overwrite": True
    }
    
    print("\n📊 Creating dashboard with 8 panels...")
    response = session.post(
        f"{GRAFANA_URL}/api/dashboards/db",
        json=dashboard,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        url = result.get('url', '')
        print(f"\n✅ Dashboard created successfully!")
        print(f"🔗 {GRAFANA_URL}{url}")
        print(f"\n📋 Panels:")
        print(f"   1. Total Messages (Stat)")
        print(f"   2. Message Rate (Stat)")
        print(f"   3. PS1 Pressure (Time Series)")
        print(f"   4. EPS1 Motor Power (Time Series)")
        print(f"   5. All Pressure Sensors (Time Series)")
        print(f"   6. Temperature Sensors (Time Series)")
        print(f"   7. Flow Sensors (Time Series)")
        print(f"   8. Sample Counts (Bar Gauge)")
        print(f"\n⏱️  Auto-refresh: 5 seconds")
        print(f"\n💡 Prometheus datasource is NATIVE - no plugins needed!")
    else:
        print(f"\n❌ Failed to create dashboard:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    create_dashboard()


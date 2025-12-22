#!/usr/bin/env python3
"""
Create Advanced Grafana Dashboard for Spark Analytics
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
    print("🎨 Creating 'Hydraulic System - Spark Analytics' Dashboard")
    print("=" * 80)
    
    # Dashboard definition
    dashboard = {
        "dashboard": {
            "title": "Hydraulic System - Spark Analytics (Deep Dive)",
            "tags": ["spark", "analytics", "insights", "hydraulic"],
            "timezone": "browser",
            "refresh": "5s",
            "panels": [
                # --- ROW 1: SPARK HEALTH ---
                {
                    "id": 1,
                    "title": "⚡ Spark Job Health (Aggregated Messages)",
                    "type": "stat",
                    "gridPos": {"x": 0, "y": 0, "w": 4, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "rate(hydraulic_analytics_messages_total[1m])",
                        "legendFormat": "Processed Msg/sec"
                    }],
                    "options": {
                        "colorMode": "value",
                        "graphMode": "area",
                        "justifyMode": "auto"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "unit": "pps", 
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 1, "color": "green"}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "⏱️ Last Update (Latency Check)",
                    "type": "stat",
                    "gridPos": {"x": 4, "y": 0, "w": 4, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "time() - hydraulic_analytics_last_update_timestamp",
                        "legendFormat": "Seconds Ago"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s",
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "green"},
                                    {"value": 10, "color": "orange"},
                                    {"value": 30, "color": "red"}
                                ]
                            }
                        }
                    }
                },
                
                # --- ROW 2: DATA SMOOTHING COMPARISON (The "Wow" Factor) ---
                {
                    "id": 3,
                    "title": "🌊 Data Smoothing Effect: PS1 Pressure (Raw vs Spark Avg)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 4, "w": 24, "h": 10},
                    "targets": [
                        {
                            "refId": "Raw",
                            "expr": 'hydraulic_raw_ps1{job="hydraulic_raw"}',
                            "legendFormat": "Raw Signal (Noisy)",
                            # Make raw signal faint
                        },
                        {
                            "refId": "Spark",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="PS1", job="hydraulic_spark"}',
                            "legendFormat": "Spark 1m Avg (Smooth)",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "lineWidth": 2,
                                "fillOpacity": 10
                            },
                            "unit": "bar"
                        },
                        "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Raw Signal (Noisy)"},
                                "properties": [
                                    {"id": "custom.lineWidth", "value": 1},
                                    {"id": "custom.lineStyle", "value": "dash"},
                                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "rgba(100, 100, 100, 0.5)"}} 
                                ]
                            },
                            {
                                "matcher": {"id": "byName", "options": "Spark 1m Avg (Smooth)"},
                                "properties": [
                                    {"id": "custom.lineWidth", "value": 4},
                                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "#FFFF00"}} # Bright Yellow
                                ]
                            }
                        ]
                    }
                },

                # --- ROW 3: VOLATILITY BANDS ---
                {
                    "id": 4,
                    "title": "📊 Volatility Bands (Min/Max Range) - Pressure Sensors",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 14, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "Max",
                            "expr": 'hydraulic_sensor_max_1m{sensor=~"PS.*"}',
                            "legendFormat": "{{sensor}} Max"
                        },
                         {
                            "refId": "Avg",
                            "expr": 'hydraulic_sensor_avg_1m{sensor=~"PS.*"}',
                            "legendFormat": "{{sensor}} Avg",
                            "hide": True # Hide Average, just show bands? Or show all.
                        },
                        {
                            "refId": "Min",
                            "expr": 'hydraulic_sensor_min_1m{sensor=~"PS.*"}',
                            "legendFormat": "{{sensor}} Min"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "drawStyle": "line",
                                "lineInterpolation": "smooth",
                                "fillOpacity": 15
                            },
                             "unit": "bar"
                        }
                    }
                },
                 {
                    "id": 5,
                    "title": "📉 System Stability Index (Standard Deviation Wrapper)",
                    "description": "Calculated as (Max - Min). Higher values indicate instability.",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 14, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'hydraulic_sensor_max_1m{sensor="PS1"} - hydraulic_sensor_min_1m{sensor="PS1"}',
                            "legendFormat": "PS1 Volatility"
                        },
                        {
                             "refId": "B",
                            "expr": 'hydraulic_sensor_max_1m{sensor="PS2"} - hydraulic_sensor_min_1m{sensor="PS2"}',
                            "legendFormat": "PS2 Volatility"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "bar",
                             "custom": {
                                "drawStyle": "bars",
                                "fillOpacity": 50
                            }
                        }
                    }
                },

                # --- ROW 4: EFFICIENCY ---
                {
                    "id": 6,
                    "title": "⚙️ Efficiency Analysis: Power vs Flow",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 22, "w": 24, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="EPS1"}',
                            "legendFormat": "Motor Power (W)",
                        },
                        {
                            "refId": "B",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="FS1"} * 100', 
                            "legendFormat": "Flow Rate (Scalex100)",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                             "custom": {
                                "drawStyle": "line",
                                "fillOpacity": 5,
                                "axisPlacement": "auto"
                            }
                        },
                         "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Motor Power (W)"},
                                "properties": [{"id": "unit", "value": "watt"}]
                            },
                             {
                                "matcher": {"id": "byName", "options": "Flow Rate (Scalex100)"},
                                "properties": [{"id": "unit", "value": "short"}] # Abstract unit
                            }
                        ]
                    }
                },

                # Removed Anomaly Timeline (Moved to dedicated dashboard)
                {
                    "id": 8,
                    "title": "📊 Statistical Feature: Standard Deviation (Variability)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 36, "w": 24, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'hydraulic_sensor_stddev_1m',
                            "legendFormat": "{{sensor}} StdDev"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "short", 
                            "custom": {"drawStyle": "line", "fillOpacity": 5}
                        }
                    }
                }
            ]
        },
        "overwrite": True
    }
    
    print("\n📊 Sending dashboard config to Grafana...")
    try:
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
            print(f"\n✨ Highlights:")
            print(f"   1. 'Data Smoothing Effect': Overlays raw (noisy) signals with Spark's calculated average.")
            print(f"   2. 'Volatility Bands': Shows the Min-Max spread, creating a visual 'tunnel' of data stability.")
            print(f"   3. 'Stability Index': Automatically calculated (Max-Min) to detect vibration/instability.")
        else:
            print(f"\n❌ Failed to create dashboard:")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("Ensure Grafana is running at localhost:3000")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    create_dashboard()

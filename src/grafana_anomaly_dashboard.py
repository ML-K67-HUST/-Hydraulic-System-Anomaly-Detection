#!/usr/bin/env python3
"""
Create Advanced Grafana Dashboard for Health & Anomalies
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
    print("🎨 Creating 'Hydraulic System - Health & Anomalies' Dashboard")
    print("=" * 80)
    
    # Dashboard definition
    dashboard = {
        "dashboard": {
            "title": "Hydraulic System - Health & Anomalies",
            "tags": ["spark", "anomalies", "health", "hydraulic"],
            "timezone": "browser",
            "refresh": "5s",
            "panels": [
                # --- ROW 1: EXECUTIVE SUMMARY (4 COLUMNS) ---
                {
                    "id": 13,
                    "title": "❤️ Overall System Health",
                    "type": "gauge",
                    "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "avg(hydraulic_sensor_health_score) or vector(100)",
                        "legendFormat": "Health Score"
                    }],
                    "options": {
                        "showThresholdLabels": False,
                        "showThresholdMarkers": True
                    },
                     "fieldConfig": {
                        "defaults": {
                            "min": 0, "max": 100, "unit": "percent",
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "red"},
                                    {"value": 80, "color": "orange"},
                                    {"value": 90, "color": "green"}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 1,
                    "title": "🚨 Active Anomalies",
                    "type": "stat",
                    "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "sum(hydraulic_anomaly_status) or vector(0)",
                        "legendFormat": "Active Issues"
                    }],
                    "options": {
                        "colorMode": "value",
                        "graphMode": "none",
                        "justifyMode": "auto",
                        "reduceOptions": {"calcs": ["last"], "values": False}
                    },
                    "fieldConfig": {
                        "defaults": {
                            "unit": "none", 
                            "decimals": 0, 
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": 0, "color": "green"},
                                    {"value": 1, "color": "red"}
                                ]
                            },
                             "mappings": [
                                {"type": "value", "options": {"0": {"text": "", "color": "green"}}},
                                {"type": "value", "options": {"1": {"text": "", "color": "red"}}}
                            ]
                        }
                    }
                },
                {
                    "id": 2,
                    "title": "📈 Anomaly Trend (1h)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "sum(hydraulic_anomaly_status)",
                        "legendFormat": "Count"
                    }],
                    "options": {
                         "legend": {"displayMode": "hidden"}
                    },
                    "fieldConfig": {
                        "defaults": {
                             "custom": {"drawStyle": "line", "fillOpacity": 20},
                             "color": {"mode": "fixed", "fixedColor": "red"},
                             "min": 0
                        }
                    }
                },
                {
                    "id": 9,
                    "title": "📊 Hourly Total",
                    "type": "stat",
                    "gridPos": {"x": 18, "y": 0, "w": 6, "h": 4},
                    "targets": [{
                        "refId": "A",
                        "expr": "sum(increase(hydraulic_anomaly_total[1h]))",
                        "legendFormat": "Count"
                    }],
                    "options": {
                         "colorMode": "value",
                         "graphMode": "area"
                    }
                },

                # --- ROW 2: SIGNAL ANALYSIS (DATA SMOOTHING) ---
                {
                    "id": 8,
                    "title": "🌊 Data Smoothing Effect: PS1 Pressure (Raw vs Spark Avg)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 4, "w": 24, "h": 8},
                    "targets": [
                        {
                            "refId": "Raw",
                            "expr": 'hydraulic_raw_ps1{job="hydraulic_raw"}',
                            "legendFormat": "Raw Signal (Noisy)",
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
                                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "#FFFF00"}}
                                ]
                            }
                        ]
                    }
                },

                # --- ROW 3: PRESSURE SUBSYSTEM ---
                {
                    "id": 13,
                    "title": "🌊 Pressure Subsystem: Anomaly Timeline",
                    "type": "state-timeline",
                    "gridPos": {"x": 0, "y": 12, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            # Use regex to strictly enforce Pressure Sensors
                            "expr": 'hydraulic_anomaly_status{sensor=~"PS.*", type=~"high_pressure|pressure_spike"}',
                            "legendFormat": "{{sensor}} - {{type}}"
                        }
                    ],
                    "options": {
                        "alignValue": "center",
                         "mergeValues": True
                    },
                    "fieldConfig": {
                         "defaults": {
                             "color": {"mode": "thresholds"},
                             "thresholds": {
                                "mode": "absolute",
                                "steps": [{"value": 0, "color": "green"}, {"value": 1, "color": "red"}]
                            },
                             "mappings": [
                                {"type": "value", "options": {"0": {"text": "", "color": "green"}}},
                                {"type": "range", "options": {"from": 0.1, "to": 100, "result": {"text": "", "color": "red"}}}
                            ]
                        }
                    }
                },
                {
                    "id": 4,
                    "title": "🌊 Pressure Stability (Standard Deviation)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 12, "w": 12, "h": 8},
                    "targets": [{
                        "refId": "A",
                        "expr": 'hydraulic_sensor_stddev_1m{sensor=~"PS.*"}',
                        "legendFormat": "{{sensor}}"
                    }],
                    "fieldConfig": {
                         "defaults": {
                            "unit": "bar",
                            "custom": {"fillOpacity": 10, "showPoints": "auto"}
                         }
                    }
                },

                # --- ROW 4: TEMPERATURE SUBSYSTEM ---
                {
                    "id": 5,
                    "title": "🔥 Temperature Subsystem: High Temp Alerts",
                    "type": "state-timeline",
                    "gridPos": {"x": 0, "y": 20, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            # Use regex to strictly enforce Temp Sensors
                            "expr": 'hydraulic_anomaly_status{sensor=~"TS.*", type="high_temperature"}',
                            "legendFormat": "{{sensor}} (Overheat)"
                        }
                    ],
                     "fieldConfig": {
                         "defaults": {
                             "color": {"mode": "thresholds"},
                             "thresholds": {
                                "mode": "absolute",
                                "steps": [{"value": 0, "color": "green"}, {"value": 1, "color": "red"}]
                            },
                             "mappings": [{"type": "value", "options": {"1": {"text": "", "color": "orange"}, "0": {"text": "", "color": "green"}}}]
                        }
                    }
                },
                 {
                    "id": 6,
                    "title": "❄️ Cooling Efficiency Matrix (Temp vs Cooling Power)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 12, "w": 12, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="TS1"}',
                            "legendFormat": "Oil Temp (TS1)"
                        },
                         {
                            "refId": "B",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="CE"}',
                            "legendFormat": "Cooling Eff (CE)"
                        }
                    ],
                    "fieldConfig": {
                         "defaults": {"unit": "celsius"}, # Approximation
                         "overrides": [{"matcher": {"id": "byName", "options": "Cooling Eff (CE)"}, "properties": [{"id": "unit", "value": "percent"}]}]
                    }
                },

                # --- ROW 4: EFFICIENCY & MOTOR ---
                {
                    "id": 7,
                    "title": "⚡ Motor Pump Efficiency (Motor Power vs Flow Rate)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 20, "w": 24, "h": 10},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="EPS1"}',
                            "legendFormat": "Motor Power (EPS1)"
                        },
                         {
                            "refId": "B",
                            "expr": 'hydraulic_sensor_avg_1m{sensor="FS1"} * 100',
                            "legendFormat": "Flow Rate x100 (FS1)"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "watt",
                            "custom": {"drawStyle": "line", "fillOpacity": 10, "axisScaling": "auto"}
                        },
                        "overrides": [
                            {
                                "matcher": {"id": "byName", "options": "Flow Rate x100 (FS1)"},
                                "properties": [{"id": "unit", "value": "none"}] # It's a scaled value
                            }
                        ]
                    }
                },

                # --- ROW 5: STATISTICAL INSIGHTS (Diverse Visualizations) ---
                 {
                    "id": 8,
                    "title": "🧭 System Vitals (Real-time Gauges)",
                    "type": "gauge",
                    "gridPos": {"x": 0, "y": 30, "w": 6, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_sensor_avg_1m{sensor="PS1"}', "legendFormat": "Pressure (PS1)"},
                        {"refId": "B", "expr": 'hydraulic_sensor_avg_1m{sensor="TS1"}', "legendFormat": "Temp (TS1)"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "min": 0, "max": 200, # Approx max for Pressure
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
                    "id": 10,
                    "title": "🥧 Anomaly Type Distribution",
                    "type": "piechart",
                    "gridPos": {"x": 6, "y": 30, "w": 6, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'sum by (type) (hydraulic_anomaly_total)', "legendFormat": "{{type}}"}
                    ],
                    "options": {"pieType": "donut", "legend": {"displayMode": "table", "placement": "right"}}
                },
                {
                    "id": 11,
                    "title": "🏆 Top Offending Sensors (Bar Gauge)",
                    "type": "bargauge",
                    "gridPos": {"x": 12, "y": 30, "w": 6, "h": 8},
                    "targets": [
                         {"refId": "A", "expr": 'topk(5, sum by (sensor) (hydraulic_anomaly_total))', "legendFormat": "{{sensor}}"}
                    ],
                    "options": {
                        "orientation": "vertical",
                        "displayMode": "gradient",
                        "showUnfilled": True
                    },
                     "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "continuous-GrYlRd"},
                             "min": 0
                        }
                    }
                },
                {
                    "id": 12,
                    "title": "🔥 Pressure Intensity Heatmap (PS1)",
                    "type": "heatmap",
                    "gridPos": {"x": 18, "y": 30, "w": 6, "h": 8},
                    "targets": [
                        {"refId": "A", "expr": 'hydraulic_sensor_avg_1m{sensor="PS1"}', "format": "heatmap"}
                    ],
                    "options": {
                        "calculate": True,
                        "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}
                    }
                }
            ]
        },
        "overwrite": True
    }
    
    # Remove the broken fallback code since we hardcoded timeseries above
    # (Previously it was targeting the wrong index [6] anyway)

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
        else:
            print(f"\n❌ Failed to create dashboard:")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    create_dashboard()

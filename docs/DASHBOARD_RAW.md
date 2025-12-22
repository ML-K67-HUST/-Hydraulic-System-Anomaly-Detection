# 📊 Hydraulic System - Raw Sensor Data Dashboard

## Executive Summary

This dashboard provides **unfiltered, real-time access** to all 17 sensors in the hydraulic test rig. Unlike aggregated views, this "digital oscilloscope" preserves every transient event, making it indispensable for:
- **Signal quality verification** (detecting sensor malfunctions)
- **Transient event analysis** (water hammer, cavitation spikes)
- **Baseline establishment** (understanding normal operating patterns)

---

## 🛠️ Architecture & Data Pipeline

```mermaid
graph LR
    A[17 Sensors] -->|Kafka Topics| B[KafkaConsumer]
    B -->|Python Client| C[Prometheus Pushgateway]
    C -->|Scrape 5s| D[Prometheus TSDB]
    D -->|PromQL| E[Grafana]
```

### Implementation Details (`src/consumer_raw.py`)

```python
# Key architectural decision: Use Pushgateway instead of direct Prometheus exporter
# Why? Short-lived batch jobs (like our consumer) work better with push model

for topic in SENSOR_TOPICS:  # 17 topics total
    sensor_name = topic.replace("hydraulic-", "")
    self.sensor_values[sensor_name] = Gauge(
        f'hydraulic_raw_{sensor_name.lower()}',
        f'{sensor_name} sensor reading',
        ['sensor'],  # CRITICAL: NO 'cycle' label to avoid cardinality explosion
        registry=self.registry
    )
```

**Design Decision Rationale:**
- **Metric Naming**: `hydraulic_raw_{sensor}` clearly distinguishes from Spark-processed metrics (`hydraulic_sensor_avg_1m`)
- **Label Strategy**: Only `sensor` label (not `cycle` or `timestamp`) to prevent Prometheus from creating infinite time series
- **Push Frequency**: Every 2 seconds balances freshness vs Pushgateway load

---

## 📉 Chart-by-Chart Analysis

### Row 0: Kafka Consumer Health Monitoring

#### 1. 📥 Message Rate (Msg/sec)
**Rationale**: Verify the data ingestion pipeline is functioning correctly.

**Query**: `rate(hydraulic_messages_total[1m])`

**Implementation Logic**:
```python
# consumer_raw.py increments this counter for EVERY message received
self.total_messages.set(self.message_count + 1)
```

**Interpretation**:
- **Expected**: ~17 msg/sec (1 Hz per sensor × 17 sensors)
- **Red (0)**: Pipeline failure
- **Green (>1)**: Healthy ingestion

#### 2. 📦 Total Messages Processed
**Rationale**: Cumulative health check - ensures no message loss over time.

**Query**: `hydraulic_messages_total`

**Why This Matters**: If this number stops incrementing but producer is running, indicates consumer crash or Kafka connectivity loss.

#### 3. ⏱️ Consumer Latency
**Rationale**: Detect processing bottlenecks before they cause backlog.

**Query**: `time() - hydraulic_last_update_timestamp`

**Threshold Logic**:
- **Green (<5s)**: Real-time processing
- **Orange (5-30s)**: Warning - consumer falling behind
- **Red (>30s)**: Critical - immediate investigation needed

---

### Row 1: Real-Time System Vitals

#### 🧭 Main System Vitals (Gauge Panel)
**Rationale**: At-a-glance health check for the 3 most critical subsystems.

**Mining Idea**: Identify the "Big 3" sensors that best represent overall health:
1. **PS1 (Pressure)**: Primary indicator of pump performance
2. **TS1 (Temperature)**: Thermal management effectiveness  
3. **FS1 (Flow Rate)**: Hydraulic power delivery

**Implementation**:
```python
"targets": [
    {"expr": 'hydraulic_raw_ps1', "legendFormat": "Pressure (PS1)"},
    {"expr": 'hydraulic_raw_ts1', "legendFormat": "Temp (TS1)"},
    {"expr": 'hydraulic_raw_fs1', "legendFormat": "Flow (FS1)"}
]
```

**Threshold Configuration**:
- Set to highlight values approaching safety limits
- Allows operator to see trending toward danger zones

#### 🌡️ Temperature Overview (Bar Gauge)
**Rationale**: Compare all 4 temperature sensors to detect **thermal imbalance** (one zone much hotter than others = cooler malfunction).

**Visual Design Choice**: LCD bar gauges provide intuitive comparison. Color gradient (Green→Yellow→Red) maps directly to thermal stress.

---

### Rows 2-3: Pressure Subsystem Deep Dive

#### Pressure Sensors TimeSeries (PS1-PS6)
**Rationale**: The 6 pressure sensors are distributed across the hydraulic circuit. Synchronized patterns reveal system-wide phenomena; divergent patterns indicate localized issues.

**Query**: `hydraulic_raw_ps{1-6}`

**Analysis Patterns to Look For**:
1. **Synchronized Spikes**: Normal pulsation from pump cycles
2. **PS1 spike, others stable**: Inlet obstruction
3. **Gradual drift from baseline**: Accumulator degradation
4. **Chaotic oscillations**: Cavitation or air entrainment

#### 🔥 Pressure Distribution Heatmaps (PS1-PS4)
**Rationale**: Traditional time-series shows **when** pressure changes. Heatmaps show **how often** each pressure value occurs.

**Mining Idea**: Inspired by spectral analysis in vibration monitoring. Identify the "normal operating envelope."

**Implementation**:
```python
"type": "heatmap",
"targets": [{"expr": 'hydraulic_raw_ps1', "format": "heatmap"}],
"options": {
    "calculate": True,
    "calculation": {"xBuckets": {"mode": "size", "value": "10s"}}
}
```

**Interpretation Guide**:
- **Tight vertical band**: Stable pressure (healthy)
- **Diffuse cloud**: High variance (investigate)
- **Bimodal distribution**: System switching between two operating modes

---

### Row 4: Temperature & Auxiliary Sensors

#### Vibration (VS1) & Cooling Efficiency
**Rationale**: These sensors have different sampling rates and units. Grouping them allows correlation analysis.

**Cross-Correlation Use Case**:
- **High VS1 + Rising TS1**: Bearing wear generating heat
- **Droppi CE + Stable TS**: Cooler fouling (reduced efficiency but temp not rising *yet*)

**Query**:
```python
"targets": [
    {"expr": 'hydraulic_raw_vs1', "legendFormat": "Vibration (VS1)"},
    {"expr": 'hydraulic_raw_ce', "legendFormat": "Cooling Eff (CE)"},
    {"expr": 'hydraulic_raw_cp', "legendFormat": "Cooling Power (CP)"},
    {"expr": 'hydraulic_raw_se', "legendFormat": "Efficiency (SE)"}
]
```

**Why Group These?**: All are **derived/calculated values** from the test rig logic, not direct physical measurements like pressure.

---

### Row 5: Flow & Power

#### Flow Rate (FS1, FS2)
**Rationale**: Two flow sensors provide redundancy. Divergence between FS1 and FS2 indicates:
- Internal leakage
- Sensor calibration drift
- Measurement location affecting readings

#### Motor Power (EPS1)
**Rationale**: Electrical input power. When correlated with **Flow × Pressure** (hydraulic output power), reveals overall system efficiency.

**Efficiency Calculation** (manual):
```
η = (Flow [L/min] × Pressure [bar] × conversion) / Power [W]
```

**Degradation Pattern**: Efficiency slowly decreasing over weeks = normal wear. Sudden 20% drop = imminent failure.

---

## 🎯 Dashboard-Specific Features

### Shared Crosshair (`graphTooltip: 1`)
**Rationale**: Essential for multi-sensor correlation. Hover on one chart, see values on all charts at that exact timestamp.

**Use Case**: "At 14:23:15, pressure spiked to 190 bar. What was vibration doing?" → Crosshair instantly shows VS1 value at 14:23:15.

---

## 🔧 Operational Procedures

### Daily Health Check (30 seconds)
1. Verify **Message Rate** is green
2. Scan **Heatmaps** for abnormal spread
3. Check **Temperature Bar Gauge** for imbalance

### Incident Investigation
1. Use **Crosshair** to correlate events across sensors
2. Export time-series data using Grafana's CSV export
3. Overlay with maintenance logs for root cause analysis

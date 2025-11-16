# 🏗️ System Architecture

Chi tiết kiến trúc và design decisions.

---

## 📊 Overview

```
┌──────────────┐
│  Data Files  │  17 sensor files (PS1-6, EPS1, FS1-2, TS1-4, CE, CP, SE, VS1)
└──────┬───────┘
       │
       v
┌──────────────────┐
│ Kafka Producer   │  Read files → Send to Kafka topics
│ (Multi-threaded) │  17 threads, accurate timing
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Kafka Cluster    │  17 topics, 1 partition each
│ (Port 9092)      │  Message buffering
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Consumer         │  Subscribe all topics
│ (Python)         │  Transform to Prometheus format
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Pushgateway      │  Receive metrics push
│ (Port 9091)      │  Batch metrics
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Prometheus       │  Scrape Pushgateway every 5s
│ (Port 9090)      │  Store time-series data
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Grafana          │  Query Prometheus
│ (Port 3000)      │  Visualize dashboards
└──────────────────┘
```

---

## 🔧 Components

### 1. Data Layer

**Files:** `data/*.txt`

Each file contains sensor readings for 2205 cycles:

- Each row = 1 cycle
- Tab-delimited values
- Different sampling rates

**Example PS1.txt:**

```
191.44  178.41  191.38  ...  151.19  [6000 values per row]
```

### 2. Producer (`src/producer.py`)

**Design:**

- **Multi-threaded:** 17 threads, 1 per sensor
- **Accurate timing:** Uses `time.sleep()` với interval chính xác
- **Real-time simulation:** Gửi data đúng sampling rate

**Sensor Configurations:**

| Sensor                 | Frequency | Samples/Cycle | Thread Interval |
| ---------------------- | --------- | ------------- | --------------- |
| PS1-6                  | 100Hz     | 6000          | 0.01s           |
| EPS1                   | 100Hz     | 6000          | 0.01s           |
| FS1-2                  | 10Hz      | 600           | 0.10s           |
| TS1-4, CE, CP, SE, VS1 | 1Hz       | 60            | 1.00s           |

**Message Format:**

```json
{
  "sensor": "PS1",
  "cycle": 0,
  "sample_idx": 100,
  "value": 151.19,
  "timestamp": "2025-11-08T14:30:45.123456",
  "sampling_rate_hz": 100
}
```

### 3. Kafka Cluster

**Topics:** 17 topics

- `hydraulic-PS1` ... `hydraulic-PS6`
- `hydraulic-EPS1`
- `hydraulic-FS1`, `hydraulic-FS2`
- `hydraulic-TS1` ... `hydraulic-TS4`
- `hydraulic-CE`, `hydraulic-CP`, `hydraulic-SE`, `hydraulic-VS1`

**Configuration:**

- Replication factor: 1 (single broker)
- Partitions: 1 per topic
- Retention: 24 hours

**Why Kafka?**

- ✅ Decoupling producer/consumer
- ✅ Buffer for high-frequency data
- ✅ Replay capability
- ✅ Horizontal scaling potential

### 4. Consumer (`src/consumer.py`)

**Design:**

- Subscribe to all 17 topics
- Transform Kafka messages → Prometheus metrics
- Push to Pushgateway every 2 seconds

**Metrics Created:**

1. **Gauges per sensor:**

```python
hydraulic_ps1_value{sensor="PS1", cycle="0"} 151.19
hydraulic_ps1_samples_total{sensor="PS1"} 6000
```

2. **Global metrics:**

```python
hydraulic_messages_total 43680
hydraulic_last_update_timestamp 1699456789.123
```

**Why Pushgateway?**

- Kafka consumer is short-lived per message
- Can't scrape directly like HTTP server
- Batch metrics for efficiency

### 5. Prometheus

**Configuration:** `prometheus.yml`

```yaml
scrape_interval: 5s

scrape_configs:
  - job_name: "pushgateway"
    honor_labels: true # Keep labels from Pushgateway
    static_configs:
      - targets: ["pushgateway:9091"]
```

**Data Retention:** 15 days (default)

**Why Prometheus?**

- ✅ Built for time-series data
- ✅ Native Grafana integration
- ✅ Powerful query language (PromQL)
- ✅ Efficient storage (compression)

### 6. Grafana

**Auto-provisioning:**

- Datasource: `grafana/provisioning/datasources/prometheus.yml`
- Dashboard: Created by `src/grafana_prometheus_dashboard.py`

**Dashboard Panels:**

| Panel          | Query                                   | Visualization |
| -------------- | --------------------------------------- | ------------- |
| Total Messages | `hydraulic_messages_total`              | Stat          |
| Message Rate   | `rate(hydraulic_messages_total[1m])`    | Stat          |
| PS1 Pressure   | `hydraulic_ps1_value{sensor="PS1"}`     | Time Series   |
| All Pressure   | `{__name__=~"hydraulic_ps[0-9]_value"}` | Time Series   |
| Temperatures   | `{__name__=~"hydraulic_ts[0-9]_value"}` | Time Series   |

---

## 🎯 Design Decisions

### Q: Why Prometheus instead of MongoDB?

**MongoDB:**

- ❌ Grafana plugin is Enterprise (paid)
- ❌ Not optimized for time-series
- ❌ Complex query syntax
- ❌ Need custom API layer

**Prometheus:**

- ✅ Native Grafana support (free)
- ✅ Designed for time-series
- ✅ Simple PromQL
- ✅ Direct integration

### Q: Why multi-threaded producer?

**Alternative:** Single thread với delay calculation

**Issues:**

- Cumulative timing errors
- Can't achieve exact sampling rates
- 100Hz would drift over time

**Our approach:**

- Each sensor = separate thread
- Independent timing per sensor
- Accurate to within 1ms

### Q: Why Pushgateway instead of direct metrics endpoint?

**Alternatives:**

1. Consumer exposes `/metrics` endpoint
2. Write custom exporter

**Issues:**

- Consumer needs to run as HTTP server
- More complex architecture
- Higher resource usage

**Pushgateway benefits:**

- Simple push model
- Batch metrics
- Consumer stays simple

---

## 📈 Data Flow Example

### 1. Producer sends 1 message

```python
# Thread for PS1 sensor
message = {
    "sensor": "PS1",
    "cycle": 0,
    "sample_idx": 42,
    "value": 151.19,
    "timestamp": "2025-11-08T14:30:45.123456",
    "sampling_rate_hz": 100
}
producer.send("hydraulic-PS1", message)
```

### 2. Kafka stores message

```
Topic: hydraulic-PS1
Partition: 0
Offset: 42
Key: null
Value: {"sensor":"PS1",...}
```

### 3. Consumer processes

```python
# Consume from Kafka
msg = consumer.poll()

# Update Prometheus gauge
sensor_values["PS1"].labels(
    sensor="PS1",
    cycle="0"
).set(151.19)

# Update counter
messages_count += 1
total_messages.set(messages_count)
```

### 4. Consumer pushes to Pushgateway

```python
# Every 2 seconds
push_to_gateway(
    "localhost:9091",
    job="hydraulic_system",
    registry=registry
)
```

### 5. Prometheus scrapes

```
# Every 5 seconds
GET http://pushgateway:9091/metrics

# Response:
hydraulic_ps1_value{sensor="PS1",cycle="0",job="hydraulic_system"} 151.19
hydraulic_messages_total{job="hydraulic_system"} 43680
```

### 6. Grafana queries

```promql
# PromQL query
hydraulic_ps1_value{sensor="PS1"}

# Returns time-series data:
[(timestamp1, 151.19), (timestamp2, 151.31), ...]
```

### 7. Grafana renders chart

- X-axis: Time
- Y-axis: Pressure value
- Line graph updating every 5s

---

## 🔢 Performance Metrics

### Throughput

**Per cycle (60 seconds):**

- Total messages: 43,680
- Average rate: 728 msg/s
- Peak rate: ~1000 msg/s (when all threads send simultaneously)

**Network bandwidth:**

- Avg message size: ~150 bytes
- Bandwidth: ~110 KB/s

### Resource Usage

**Producer:**

- CPU: 5-10% (17 threads)
- Memory: ~50MB
- Network: Minimal

**Consumer:**

- CPU: 3-5%
- Memory: ~80MB
- Network: Minimal

**Prometheus:**

- CPU: 1-2%
- Memory: ~200MB
- Disk: ~10MB/day

**Grafana:**

- CPU: 1-2%
- Memory: ~150MB

### Latency

- Producer → Kafka: < 1ms
- Kafka → Consumer: < 5ms
- Consumer → Pushgateway: < 1ms
- Pushgateway → Prometheus: < 5s (scrape interval)
- Prometheus → Grafana: < 100ms

**Total latency:** ~5-6 seconds from sensor → dashboard

---

## ⚡ Optional: Spark Structured Streaming

Spark Structured Streaming là một **optional component** cho advanced analytics và complex aggregations.

### Architecture with Spark

```
Kafka Topics → [Python Consumer → Prometheus → Grafana]  (Core - Real-time monitoring)
              → [Spark Streaming → Aggregations]         (Optional - Advanced analytics)
```

### When to Use Spark Streaming

**Use Spark when you need:**

- ✅ Window-based aggregations (1-minute, 5-minute, hourly)
- ✅ Complex event processing
- ✅ Statistical analysis (stddev, percentiles)
- ✅ Multi-sensor correlations
- ✅ ML model inference on streaming data

**Stick with Python Consumer when:**

- ✅ Simple real-time monitoring
- ✅ Basic metrics (current values, counts)
- ✅ Low latency requirements
- ✅ Minimal resource usage

### Spark Streaming Consumer

**File:** `src/spark_streaming_consumer.py`

**Features:**

- Reads from all 17 Kafka topics
- 1-minute window aggregations
- Per-sensor metrics: count, avg, max, min, sum
- Watermark handling for late data
- Checkpoint-based fault tolerance

**Output:**

- Console (for monitoring)
- In-memory table (queryable via Spark SQL)

**See:** [SPARK_STREAMING.md](SPARK_STREAMING.md) for complete guide

---

## 🔄 Scaling Considerations

### Current Setup (Single Machine)

- 1 Kafka broker
- 1 Prometheus instance
- 1 Grafana instance
- Can handle: **~1000 msg/s**

### Scaling Options

#### 1. Horizontal Kafka Scaling

```yaml
# Add more brokers
kafka-2:
  image: confluentinc/cp-kafka:7.5.0
  ...

kafka-3:
  image: confluentinc/cp-kafka:7.5.0
  ...
```

**Increase:**

- Replication factor: 3
- Partitions: 3+ per topic
- Throughput: 3-5x

#### 2. Consumer Group Scaling

```python
# Multiple consumers with same group_id
CONSUMER_GROUP = "hydraulic-prometheus-group"

# Kafka auto-balances partitions
```

#### 3. Prometheus Federation

```yaml
# Remote write to central Prometheus
remote_write:
  - url: http://central-prometheus:9090/api/v1/write
```

#### 4. Grafana Load Balancing

- Multiple Grafana instances
- Share same Prometheus backend
- Nginx load balancer

---

## 🛠️ Technology Choices

| Component      | Technology | Alternatives          | Why Chosen                         |
| -------------- | ---------- | --------------------- | ---------------------------------- |
| Message Queue  | Kafka      | RabbitMQ, Redis       | Industry standard, high throughput |
| Time-Series DB | Prometheus | InfluxDB, TimescaleDB | Native Grafana, simple setup       |
| Visualization  | Grafana    | Kibana, Tableau       | Open source, powerful, free        |
| Language       | Python     | Java, Go              | Rapid development, rich libraries  |
| Container      | Docker     | Kubernetes            | Simple, local development          |

---

## 📊 Comparison: Old vs New Architecture

### Old (MongoDB + Grafana)

```
Producer → Kafka → Consumer → MongoDB → REST API → Grafana
                                          ↑
                                     Enterprise Plugin ❌
```

**Issues:**

- Grafana MongoDB plugin is paid
- Need custom REST API
- Complex JSON queries
- Slow dashboard updates

### New (Prometheus + Grafana)

```
Producer → Kafka → Consumer → Pushgateway → Prometheus → Grafana
                                                           ↑
                                                   Native Support ✅
```

**Benefits:**

- No plugins needed
- Direct integration
- Simple PromQL
- Fast, real-time updates

---

## 🎓 Learning Points

1. **Time-series data ≠ Document database**

   - Prometheus >> MongoDB for metrics

2. **Push vs Pull models**

   - Prometheus scrapes (pull)
   - Pushgateway enables batch jobs (push)

3. **Multi-threading for real-time**

   - Required for accurate timing
   - Each sensor needs independent clock

4. **Decoupling with message queues**

   - Kafka buffers data
   - Allows replay
   - Producer/consumer can scale independently

5. **Observability stack**
   - Prometheus: Metrics
   - Grafana: Visualization
   - Industry standard combination

---

## 🔮 Future Improvements

1. **Anomaly Detection:**

   - Add ML model consumer
   - Detect abnormal patterns
   - Alert on anomalies

2. **Data Persistence:**

   - Add MongoDB consumer (parallel)
   - Long-term storage
   - Historical analysis

3. **Stream Processing (Optional):**

   - Spark Structured Streaming consumer available (`src/spark_streaming_consumer.py`)
   - Real-time aggregations with window operations
   - Complex event processing
   - See [SPARK_STREAMING.md](SPARK_STREAMING.md) for details

4. **Alerting:**
   - Prometheus Alertmanager
   - Threshold-based alerts
   - Slack/email notifications

---

Tất cả design decisions đều hướng tới mục tiêu: **Simple, Fast, Free** 🚀

# 🚀 Streaming Job Deployment Guide

Hướng dẫn triển khai `streaming_job.py` theo kế hoạch chi tiết.

---

## 📋 Overview

`streaming_job.py` là Spark Structured Streaming job thực hiện:

- ✅ Đọc dữ liệu từ Kafka
- ✅ Xử lý với windowing và watermarking
- ✅ Phát hiện bất thường (rule-based)
- ✅ Ghi đồng thời ra **HDFS** (cold sink) và **MongoDB** (hot sink)

---

## 🏗️ Architecture

```
Kafka Topics → Spark Streaming → Windowing/Watermarking → Anomaly Detection
                                                              ↓
                                    ┌─────────────────────────┴─────────────────────────┐
                                    ↓                                                 ↓
                              HDFS (Parquet)                                    MongoDB
                              (Cold Sink)                                       (Hot Sink)
                              - Batch Processing                                - Alerts
                              - ML Training                                     - Latest Metrics
```

---

## 📁 Files

### Core Files

- **`src/streaming_job.py`** - Main Spark Streaming application
- **`config/spark/streaming.yaml`** - Configuration file

### Scripts

- **`scripts/submit_streaming_job.sh`** - Submit job to Spark cluster

---

## ⚙️ Configuration

### File: `config/spark/streaming.yaml`

#### Spark Settings

```yaml
spark_app:
  name: "HydraulicSystemStreaming"
  master: "spark://spark-master:7077" # hoặc "local[*]" để test
```

#### Kafka Input

```yaml
kafka:
  bootstrap_servers: "kafka:9092" # Docker network
  bootstrap_servers_host: "localhost:29092" # From host
  subscribe_topic: "hydraulic_data" # Topic name
  schema_path: "config/kafka/schema.json"
  starting_offsets: "latest"
```

#### Processing Logic

```yaml
processing:
  trigger_interval: "1 minute"
  checkpoint_location: "/tmp/spark-checkpoints/streaming_job"

logic:
  window_duration: "5 minutes"
  slide_duration: "1 minute"
  watermark_delay: "10 minutes"
```

#### Anomaly Detection Rules

```yaml
rules:
  max_pressure: 3000 # bar
  max_temperature: 120 # Celsius
  min_cooler_efficiency: 0.5 # 50%
```

#### Sinks

```yaml
sinks:
  cold_sink_hdfs:
    enabled: true
    path: "/tmp/data/processed/hydraulic_system" # Local path
    format: "parquet"
    partition_by: "processing_date"

  hot_sink_mongo:
    enabled: true
    uri: "mongodb://mongodb:27017/hydraulic_db"
    database: "hydraulic_db"
    collection_alerts: "alerts"
    collection_metrics: "latest_metrics"
```

---

## 🚀 Deployment Steps

### Step 1: Prerequisites

```bash
# 1. Start all required services
docker-compose -f docker-compose.khang.yml up -d \
  zookeeper kafka spark-master spark-worker mongodb

# 2. Wait for services to be ready
sleep 10

# 3. Verify services
docker ps | grep -E "kafka|spark|mongodb"
```

### Step 2: Verify Kafka Topic

```bash
# Check if topic exists (or create it)
docker exec -it <kafka-container> \
  kafka-topics --list --bootstrap-server localhost:9092

# If using single topic "hydraulic_data", create it:
docker exec -it <kafka-container> \
  kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic hydraulic_data \
    --partitions 1 \
    --replication-factor 1
```

**Note:** Hiện tại producer gửi vào 17 topics riêng (`hydraulic-PS1`, `hydraulic-PS2`, ...). Có 2 options:

1. **Option A:** Sử dụng Kafka topic pattern:

   ```yaml
   subscribe_topic: "hydraulic-*" # Subscribe to all hydraulic topics
   ```

2. **Option B:** Tạo một topic tổng hợp và producer gửi vào đó

### Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# PySpark và packages sẽ được download khi submit job
```

### Step 4: Submit Job

```bash
# Submit to Spark cluster
./scripts/submit_streaming_job.sh
```

**Hoặc manually:**

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  src/streaming_job.py
```

---

## 🔍 Monitoring

### Spark UI

- **Master UI:** http://localhost:8080
- **Application UI:** http://localhost:4040 (when job running)

### MongoDB

```bash
# Connect to MongoDB
docker exec -it <mongodb-container> mongosh

# Check collections
use hydraulic_db
show collections

# Query alerts
db.alerts.find().pretty()

# Query latest metrics
db.latest_metrics.find().sort({latest_timestamp_in_window: -1}).limit(10).pretty()
```

### Checkpoints

```bash
# Check checkpoint directory
ls -la /tmp/spark-checkpoints/streaming_job/
```

---

## 🐛 Troubleshooting

### Issue 1: Kafka Connection Failed

**Error:** `NoBrokersAvailable`

**Solution:**

```bash
# Check Kafka is running
docker ps | grep kafka

# Check Kafka broker address in config
# Use bootstrap_servers_host for local development
```

### Issue 2: Schema Mismatch

**Error:** `Cannot resolve column` or schema errors

**Solution:**

- Verify `config/kafka/schema.json` matches message format
- Check producer message format
- Adjust column names in `streaming_job.py` if needed

### Issue 3: MongoDB Connection Failed

**Error:** `MongoException` or connection timeout

**Solution:**

```bash
# Check MongoDB is running
docker ps | grep mongodb

# Test connection
docker exec -it <mongodb-container> mongosh --eval "db.adminCommand('ping')"

# Update URI in config if needed
```

### Issue 4: HDFS Path Not Found

**Error:** `Path does not exist` (if using HDFS)

**Solution:**

- For development, use local filesystem path in config:
  ```yaml
  cold_sink_hdfs:
    path: "/tmp/data/processed/hydraulic_system"
  ```
- Ensure directory exists or Spark will create it

### Issue 5: Checkpoint Errors

**Error:** Checkpoint corruption or incompatible changes

**Solution:**

```bash
# Clear checkpoint (⚠️ Will lose state)
rm -rf /tmp/spark-checkpoints/streaming_job

# Restart job
```

---

## 📊 Data Flow

### Input (Kafka)

- Messages từ producer với format:
  ```json
  {
    "sensor": "PS1",
    "cycle": 0,
    "sample_idx": 0,
    "value": 151.19,
    "timestamp": "2025-11-08T14:30:45.123456",
    "sampling_rate_hz": 100
  }
  ```

### Processing

1. **Parse JSON** với schema
2. **Windowing:** 5-minute windows, 1-minute slide
3. **Aggregations:** avg, max, min per window
4. **Anomaly Detection:** Rule-based (pressure, temperature, efficiency)

### Output

#### HDFS (Cold Sink)

- **Format:** Parquet
- **Partition:** By `processing_date`
- **Content:** All aggregated data
- **Use case:** Batch processing, ML training

#### MongoDB (Hot Sink)

- **Collection `alerts`:** Only anomaly records

  ```json
  {
    "window": {...},
    "device_id": "PS1",
    "alert_type": "High Pressure",
    "avg_pressure": 3200,
    "max_temperature": 115,
    "latest_timestamp_in_window": "2025-11-08T14:35:00Z"
  }
  ```

- **Collection `latest_metrics`:** All metrics
  ```json
  {
    "window": {...},
    "device_id": "PS1",
    "avg_pressure": 1500,
    "max_temperature": 80,
    "min_cooler_efficiency": 0.75
  }
  ```

---

## 🔮 Future Enhancements (Phase 3)

### ML Integration

1. Load ML model from HDFS
2. Apply model inference in `foreachBatch`
3. Add `ml_based_anomaly` column
4. Update alerts to include ML predictions

### Schema Evolution

- Coordinate with producer team for unified schema
- Support multiple message formats
- Schema registry integration

---

## 📚 References

- [Spark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Kafka Integration](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)
- [MongoDB Connector](https://www.mongodb.com/docs/spark-connector/current/)

---

**Last Updated:** 2025-11-08  
**Status:** Phase 2 - Rule-based Anomaly Detection  
**Next:** Phase 3 - ML Integration

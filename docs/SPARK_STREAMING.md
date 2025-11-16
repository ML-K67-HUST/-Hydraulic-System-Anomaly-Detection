# ⚡ Spark Structured Streaming Guide

Hướng dẫn sử dụng Spark Structured Streaming cho Hydraulic System Anomaly Detection.

---

## 📊 Overview

Spark Structured Streaming cho phép:
- **Real-time aggregations** - Tính toán thống kê theo thời gian thực
- **Window operations** - Phân tích theo cửa sổ thời gian
- **Complex event processing** - Xử lý sự kiện phức tạp
- **Scalable processing** - Xử lý song song, phân tán

### Architecture

```
Kafka Topics → Spark Streaming → Aggregations → (Console/Memory/Database)
```

---

## 🚀 Quick Start

### Option 1: Local Mode (Development)

```bash
# 1. Install PySpark
pip install pyspark

# 2. Start Kafka
docker-compose -f docker-compose.khang.yml up -d kafka zookeeper

# 3. Run streaming locally
./scripts/run_spark_streaming_local.sh
```

### Option 2: Spark Cluster Mode

```bash
# 1. Start Spark cluster
docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker

# 2. Submit job
./scripts/submit_spark_streaming.sh
```

---

## 📁 Files

### Source Code
- **`src/spark_streaming_consumer.py`** - Main Spark Streaming application
  - Reads from Kafka topics
  - Performs window aggregations (1-minute windows)
  - Outputs to console and memory

### Configuration
- **`config/spark/spark-defaults.conf`** - Spark configuration
- **`config/spark/log4j.properties`** - Logging configuration

### Scripts
- **`scripts/submit_spark_streaming.sh`** - Submit to Spark cluster
- **`scripts/run_spark_streaming_local.sh`** - Run locally

---

## 🔧 Configuration

### Spark Settings

File: `config/spark/spark-defaults.conf`

Key settings:
- **Memory:** 2GB driver, 2GB executor
- **Checkpoint:** `/tmp/spark-checkpoints/hydraulic-streaming`
- **Window size:** 1 minute
- **Watermark:** 10 seconds

### Kafka Settings

In `src/spark_streaming_consumer.py`:
```python
KAFKA_BROKER = "localhost:29092"
KAFKA_TOPICS = "hydraulic-PS1,hydraulic-PS2,..."
```

---

## 📊 Aggregations

Spark Streaming tính toán các metrics sau:

### Per Sensor (1-minute windows):
- **Count:** Số lượng messages
- **Average:** Giá trị trung bình
- **Max:** Giá trị lớn nhất
- **Min:** Giá trị nhỏ nhất
- **Sum:** Tổng giá trị

### Output Format:
```
+------------------------------------------+-------+-------------+----------+----------+----------+
|window                                    |sensor |message_count|avg_value |max_value |min_value |
+------------------------------------------+-------+-------------+----------+----------+----------+
|[2025-11-08 14:30:00, 2025-11-08 14:31:00]|PS1    |6000         |151.23    |191.44    |120.15    |
+------------------------------------------+-------+-------------+----------+----------+----------+
```

---

## 🎯 Use Cases

### 1. Real-time Monitoring
- Monitor average pressure across all sensors
- Detect anomalies (values outside normal range)
- Track message rates

### 2. Window Analysis
- 1-minute averages for dashboard
- 5-minute trends
- Hourly summaries

### 3. Anomaly Detection
- Compare current values vs historical averages
- Flag sensors with unusual patterns
- Alert on threshold breaches

### 4. Data Export
- Write aggregations to database
- Export to Parquet for analysis
- Send to Prometheus for Grafana

---

## 🔄 Running the Application

### Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install PySpark
pip install pyspark

# Run locally
python src/spark_streaming_consumer.py
```

**Output:**
- Console: Aggregated results every 10 seconds
- Spark UI: http://localhost:4040

### Cluster Mode

```bash
# Start Spark cluster
docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker

# Wait for services
sleep 10

# Submit job
./scripts/submit_spark_streaming.sh
```

**Monitor:**
- Spark Master UI: http://localhost:8080
- Spark Application UI: http://localhost:4040

---

## 📈 Example Queries

### Query In-Memory Table

Spark writes results to in-memory table `hydraulic_aggregations`:

```python
# In Spark shell or separate script
spark.sql("""
    SELECT sensor, avg_value, max_value, min_value
    FROM hydraulic_aggregations
    WHERE window.end > current_timestamp() - interval 5 minutes
    ORDER BY sensor
""").show()
```

### Custom Aggregations

Modify `process_stream()` function in `spark_streaming_consumer.py`:

```python
# Example: Add standard deviation
from pyspark.sql.functions import stddev

windowed = df \
    .withWatermark("event_timestamp", "10 seconds") \
    .groupBy(
        window("event_timestamp", "1 minute"),
        "sensor"
    ) \
    .agg(
        avg("value").alias("avg_value"),
        stddev("value").alias("stddev_value"),  # New
        max("value").alias("max_value"),
        min("value").alias("min_value")
    )
```

---

## 🔧 Troubleshooting

### Issue 1: Kafka Connection Failed

```bash
# Check Kafka is running
docker ps | grep kafka

# Check Kafka broker address
# Should be: localhost:29092 (from host) or kafka:9092 (from Docker)
```

### Issue 2: Spark Not Starting

```bash
# Check Spark services
docker ps | grep spark

# Check logs
docker logs hydraulic-system-anomaly-detection-spark-master-1
docker logs hydraulic-system-anomaly-detection-spark-worker-1
```

### Issue 3: Checkpoint Errors

```bash
# Clear checkpoint directory
docker exec spark-master rm -rf /tmp/spark-checkpoints/hydraulic-streaming

# Or mount checkpoint to host for persistence
# In docker-compose.khang.yml, add volume mount
```

### Issue 4: Out of Memory

Increase memory in `spark-defaults.conf`:
```conf
spark.driver.memory              4g
spark.executor.memory            4g
```

---

## 📊 Performance

### Throughput
- **Input:** ~728 messages/second (average)
- **Processing:** 1-minute windows, 10-second triggers
- **Output:** ~6 aggregation records per minute (per sensor)

### Resource Usage
- **Driver:** ~500MB-1GB
- **Executor:** ~1-2GB
- **Network:** Minimal (local Kafka)

### Latency
- **Processing:** < 1 second
- **Window output:** Every 10 seconds
- **End-to-end:** ~10-15 seconds (Kafka → Spark → Output)

---

## 🔮 Future Enhancements

### 1. Write to Prometheus
```python
# Push aggregations to Prometheus Pushgateway
from prometheus_client import push_to_gateway

def write_to_prometheus(df):
    # Convert Spark DataFrame to Prometheus metrics
    # Push to Pushgateway
    pass
```

### 2. Anomaly Detection
```python
# Add ML model inference
from pyspark.ml import PipelineModel

model = PipelineModel.load("models/anomaly_detector")
predictions = model.transform(df)
```

### 3. Multiple Outputs
```python
# Write to multiple sinks
query1 = df.writeStream.format("console")...
query2 = df.writeStream.format("parquet")...
query3 = df.writeStream.format("kafka")...
```

### 4. Longer Windows
```python
# 5-minute and 1-hour windows
windowed_5min = df.groupBy(window("event_timestamp", "5 minutes"), "sensor")
windowed_1hour = df.groupBy(window("event_timestamp", "1 hour"), "sensor")
```

---

## 📚 References

- [Spark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Kafka Integration](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)
- [Window Operations](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html#window-operations-on-event-time)

---

## 🎓 Learning Points

1. **Watermarks:** Handle late-arriving data
2. **Checkpoints:** Enable fault tolerance
3. **Window Operations:** Time-based aggregations
4. **Output Modes:** Complete, Update, Append
5. **Kafka Integration:** Direct stream from Kafka topics

---

Happy streaming! 🚀


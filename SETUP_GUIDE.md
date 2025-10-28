# Hydraulic System Anomaly Detection - Setup & Running Guide

## Prerequisites

- Docker & Docker Compose installed
- Python 3.8+ installed
  
## Quick Start (TL;DR)

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Create Kafka topic (wait 30s after step 1)
docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --create --topic hydraulic_sensor_data --partitions 8 --replication-factor 1

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run producer (terminal 1)
python producer.py --config config/kafka/producer.yaml

# 5. Run streaming job (terminal 2)
spark-submit --master spark://spark-master:7077 streaming_job.py --config config/spark/streaming.yaml
```

---

## Detailed Setup Instructions

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pandas`, `pyarrow` - Data processing
- `kafka-python`, `confluent-kafka` - Kafka clients
- `pyspark` - Spark processing (version 3.5.0)
- `python-dotenv` - Environment configuration
- `pydantic`, `jsonschema` - Schema validation
- `pyyaml` - YAML configuration

### Step 2: Verify Configuration

All critical configurations have been fixed:
- ✓ `.env` file created with `KAFKA_BROKERS=kafka:9092`
- ✓ `data/` directory created
- ✓ PySpark added to requirements.txt
- ✓ `cooler_condition` field added to schema.json

**Check your .env file:**
```bash
cat .env
```

Key settings:
- `KAFKA_BROKERS=kafka:9092` (uses Docker service name)
- `PRODUCER_CSV_PATH=./data/hydraulic_system.csv`
- `MONGO_URI=mongodb://mongo:27017`
- `HDFS_NAMENODE_URI=hdfs://namenode:8020`

### Step 3: Prepare Your CSV File

Place your CSV at: `./data/hydraulic_system.csv`

**Required columns:**
- `device_id` - Equipment identifier (string)
- `cycle_index` - Operation cycle number (integer)
- `event_time` - Timestamp (format: YYYY-MM-DD HH:MM:SS)
- `cooler_efficiency_pct` - Cooler efficiency % (float, 0-100)
- `pressure1_bar` - Pressure sensor 1 (float, bar)
- `pressure2_bar` - Pressure sensor 2 (float, bar)
- `temperature_cooler_out_C` - Temperature output (float, Celsius)
- `cooler_condition` - Condition label (string: "normal", "degraded", "faulty")


### Step 4: Start Docker Infrastructure

```bash
docker compose up -d
```

**Services started:**
- **Zookeeper** (port 2181) - Kafka coordination
- **Kafka** (port 9092) - Message broker
- **Spark Master** (port 7077, 8080) - Distributed processing master
- **Spark Worker** - Processing worker node
- **HDFS Namenode** (port 9870) - Distributed storage master
- **HDFS Datanode** - Storage worker node
- **MongoDB** (port 27017) - Document database for alerts

**Verify services:**
```bash
docker compose ps
```

All services should show "Up" status.

**Wait 30-60 seconds** for services to fully initialize.

### Step 5: Create Kafka Topic

```bash
docker exec -it kafka \
  kafka-topics --bootstrap-server kafka:9092 \
  --create --topic hydraulic_sensor_data \
  --partitions 8 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000
```

**Topic configuration:**
- 8 partitions (for parallel processing)
- 1 replication factor (single broker)
- 7 day retention (604800000 ms)

**Verify topic created:**
```bash
docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list
```

---

## Running the System

### Run Producer (Terminal 1)

```bash
python producer.py --config config/kafka/producer.yaml
```

**What it does:**
1. Reads `./data/hydraulic_system.csv`
2. Converts each row to JSON
3. Publishes to Kafka topic `hydraulic_sensor_data`
4. Uses `device_id` as message key (ensures ordering per device)
5. Rate: ~200 messages/second (configurable via `PRODUCER_SLEEP_SECONDS`)

**Expected output:**
```
Loading configuration from config/kafka/producer.yaml
Connecting to Kafka: kafka:9092
Reading CSV: ./data/hydraulic_system.csv
Publishing messages...
Sent 1000 records...
Sent 2000 records...
```

**Leave this running** until all CSV data is published.

### Run Spark Streaming Job (Terminal 2)

```bash
spark-submit \
  --master spark://spark-master:7077 \
  streaming_job.py --config config/spark/streaming.yaml
```

**What it does:**
1. **Consumes** from Kafka topic in real-time
2. **Validates** against schema (config/kafka/schema.json)
3. **Processes** with event-time semantics
4. **Watermarks** - handles late data up to 10 minutes
5. **Windows** - 5-minute windows sliding every 1 minute
6. **Aggregates** per device per window:
   - Average cooler efficiency
   - Max/Min temperatures
   - Average pressures
   - Record counts
7. **Detects anomalies:**
   - Alert if avg efficiency < 20%
   - Alert if max temperature > 75°C
8. **Writes outputs:**
   - Alerts → MongoDB `hydraulic.alerts`
   - Latest metrics → MongoDB `hydraulic.latest_metrics`
   - Raw data → HDFS `/data/hydraulic/raw/`
   - Aggregates → HDFS `/data/hydraulic/aggregates/`

**Expected output:**
```
Starting Spark Structured Streaming...
Kafka source: kafka:9092, topic: hydraulic_sensor_data
Watermark: 10 minutes
Window: 5 minutes, slide: 1 minute
-------------------------------------------
Batch: 0
-------------------------------------------
Processed 500 records
Alerts generated: 0
-------------------------------------------
Batch: 1
-------------------------------------------
Processed 485 records
Alerts generated: 2
```

**Leave this running** for continuous processing.

---

## Optional: Batch Jobs

### Run Batch Reports

```bash
spark-submit batch_reports.py --config config/batch/reports.yaml
```

**What it does:**
- Reads historical data from HDFS
- Generates daily/weekly summary reports
- Analyzes trends over time
- Outputs to HDFS `/reports/hydraulic/`

**When to run:**
- After streaming has collected some data
- Scheduled via cron for periodic reports

### Run ML Training

```bash
spark-submit training_job.py --config config/batch/training.yaml
```

**What it does:**
- Reads historical data from HDFS
- Features: `cooler_efficiency_pct`, `pressure1_bar`, `pressure2_bar`, `temperature_cooler_out_C`
- Label: `cooler_condition`
- Algorithm: Decision Tree Classifier (configurable)
- Train/Test split: 80/20
- Outputs model to HDFS `/models/hydraulic/`

**When to run:**
- After sufficient training data collected
- Periodically for model retraining

---

## System Architecture

```
┌─────────────────┐
│   CSV File      │
│   (data/)       │
└────────┬────────┘
         │
         │ 1. Producer reads and publishes
         ▼
┌──────────────────┐
│  producer.py     │
└────────┬─────────┘
         │
         │ 2. Messages to Kafka
         ▼
┌───────────────────────┐
│   Kafka Broker        │
│   hydraulic_sensor_   │
│   data topic          │
└──────────┬────────────┘
           │
           │ 3. Spark consumes stream
           ▼
┌────────────────────────────┐
│  streaming_job.py          │
│  (Spark Structured         │
│   Streaming)               │
│                            │
│  • Validate schema         │
│  • Window aggregation      │
│  • Anomaly detection       │
│  • Multi-sink output       │
└──────┬──────────────────┬──┘
       │                  │
       │ 4a. Alerts      │ 4b. Raw data
       ▼                  ▼
┌─────────────┐    ┌───────────────┐
│  MongoDB    │    │     HDFS      │
│             │    │               │
│  • Alerts   │    │  • Raw data   │
│  • Metrics  │    │  • Aggregates │
└─────────────┘    └───────┬───────┘
                           │
                           │ 5. Batch processing
                           ▼
                 ┌──────────────────┐
                 │  batch_reports.py│
                 │  training_job.py │
                 │                  │
                 │  • Analytics     │
                 │  • ML training   │
                 └──────────────────┘
```

---

## How the System Works

### Kappa Architecture

This project implements **Kappa Architecture**:
- Stream processing for both real-time and batch workloads
- Single processing engine (Spark) for consistency
- Data replay capability via Kafka retention
- Simpler than Lambda architecture (no separate batch layer)

### Data Flow

1. **Ingestion Layer (Producer)**
   - Reads CSV as data source
   - Simulates real-time sensor streams
   - Publishes to Kafka with device_id keying

2. **Message Broker (Kafka)**
   - Durable message storage (7 days)
   - Partitioning for parallelism (8 partitions)
   - Multiple consumers support

3. **Stream Processing (Spark)**
   - Real-time event processing
   - Windowed aggregations
   - Stateful operations
   - Exactly-once semantics

4. **Serving Layer (MongoDB)**
   - Low-latency reads for dashboards
   - Alert storage for notifications
   - Current state tracking

5. **Analytics Layer (HDFS)**
   - Long-term storage (years)
   - Parquet format (columnar, compressed)
   - Batch analytics and ML training

### Windowing Strategy

- **Window size:** 5 minutes
- **Slide interval:** 1 minute (sliding windows)
- **Watermark:** 10 minutes (handles late data)

Example: Data arriving at 10:15 with event_time 10:05 is still processed (within watermark).

### Anomaly Detection Rules

Configured in `.env`:
```
ALERT_COOLER_EFFICIENCY_MIN_PCT=20  # Alert if efficiency < 20%
ALERT_TEMPERATURE_MAX_C=75          # Alert if temp > 75°C
```

Applied on windowed aggregates:
- If 5-min average efficiency < 20% → Generate alert
- If 5-min max temperature > 75°C → Generate alert

---

## Monitoring

### Spark UI
**URL:** http://localhost:8080

View:
- Running/completed applications
- Executor status and resource usage
- Job/stage/task details
- Streaming statistics

### HDFS UI
**URL:** http://localhost:9870

View:
- Filesystem browser
- Storage capacity and usage
- Datanode health
- Block information

### Check Kafka Messages

```bash
# List topics
docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list

# View messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic hydraulic_sensor_data \
  --from-beginning \
  --max-messages 10
```

### Check MongoDB Data

```bash
# Connect to MongoDB
docker exec -it mongo mongosh

# In mongosh:
use hydraulic
db.alerts.find().pretty()
db.latest_metrics.find().pretty()
```

### Check HDFS Data

```bash
# List directories
docker exec -it namenode hdfs dfs -ls /data/hydraulic/raw
docker exec -it namenode hdfs dfs -ls /data/hydraulic/aggregates

# Check storage usage
docker exec -it namenode hdfs dfs -du -h /data/hydraulic
```

### View Docker Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs kafka
docker compose logs spark-master
docker compose logs mongo

# Follow logs in real-time
docker compose logs -f kafka
```

---

## Troubleshooting

### Issue: Connection refused to kafka:9092

**Symptoms:**
```
KafkaConnectionError: Connection refused
```

**Solutions:**
1. Check Docker containers: `docker compose ps`
2. Verify all services are "Up"
3. Wait 30 seconds after `docker compose up` for initialization
4. Check `.env` has `KAFKA_BROKERS=kafka:9092` (not localhost)

### Issue: CSV file not found

**Symptoms:**
```
FileNotFoundError: ./data/hydraulic_system.csv
```

**Solutions:**
1. Verify file exists: `ls -la data/`
2. Check you're in project root directory: `pwd`
3. Verify path in producer.yaml matches actual location

### Issue: Topic does not exist

**Symptoms:**
```
Topic hydraulic_sensor_data does not exist
```

**Solutions:**
1. Create topic using command in Step 5
2. Verify: `docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list`

### Issue: ModuleNotFoundError: pyspark

**Symptoms:**
```
ModuleNotFoundError: No module named 'pyspark'
```

**Solutions:**
1. Install dependencies: `pip install -r requirements.txt`
2. Verify: `pip list | grep pyspark`
3. Use correct Python environment/virtualenv

### Issue: Spark job shows "No new data"

**Symptoms:**
Streaming job runs but processes 0 records

**Solutions:**
1. Verify producer is running and publishing
2. Check Kafka has messages: `docker exec -it kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic hydraulic_sensor_data --from-beginning --max-messages 5`
3. Check topic name matches in both producer and consumer configs

### Issue: HDFS connection refused

**Symptoms:**
```
java.net.ConnectException: Connection refused to namenode:8020
```

**Solutions:**
1. Check namenode is running: `docker compose ps namenode`
2. Verify from inside Spark container: `docker exec -it spark-master ping namenode`
3. Check HDFS UI: http://localhost:9870

---

## Stopping the System

### Stop all services (keeps data):
```bash
docker compose down
```

### Stop and remove all data (WARNING):
```bash
docker compose down -v
```

This deletes all Docker volumes including:
- Kafka messages
- HDFS data
- MongoDB data
- Zookeeper state

### Stop Python processes:
- Press `Ctrl+C` in terminal
- Or: `pkill -f producer.py`
- Or: `pkill -f spark-submit`

---

## Performance Tuning

### Adjust Producer Rate

In `.env`:
```
PRODUCER_SLEEP_SECONDS=0.005  # 200 msgs/sec
PRODUCER_SLEEP_SECONDS=0.001  # 1000 msgs/sec
```

### Adjust Kafka Partitions

More partitions = more parallelism:
```bash
--partitions 16  # Instead of 8
```

### Adjust Spark Resources

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --executor-cores 4 \
  --executor-memory 4g \
  --driver-memory 2g \
  streaming_job.py
```

### Adjust Window Size

In `.env`:
```
SPARK_WINDOW_MINUTES=10      # Larger windows = fewer updates
SPARK_WINDOW_SLIDE_MINUTES=5 # Larger slides = less overlap
```

---

## Configuration Reference

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BROKERS` | kafka:9092 | Kafka broker address |
| `KAFKA_TOPIC` | hydraulic_sensor_data | Topic name |
| `PRODUCER_CSV_PATH` | ./data/hydraulic_system.csv | CSV file location |
| `PRODUCER_SLEEP_SECONDS` | 0.005 | Delay between messages |
| `SPARK_CHECKPOINT_DIR` | hdfs://namenode:8020/... | Streaming checkpoint |
| `SPARK_WINDOW_MINUTES` | 5 | Window size |
| `SPARK_WATERMARK_MINUTES` | 10 | Late data tolerance |
| `ALERT_COOLER_EFFICIENCY_MIN_PCT` | 20 | Efficiency alert threshold |
| `ALERT_TEMPERATURE_MAX_C` | 75 | Temperature alert threshold |
| `MONGO_URI` | mongodb://mongo:27017 | MongoDB connection |
| `HDFS_NAMENODE_URI` | hdfs://namenode:8020 | HDFS connection |

---



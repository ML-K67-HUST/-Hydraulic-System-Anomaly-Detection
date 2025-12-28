# 🚀 Spark Streaming - Real-time Data Processing
## Slide Presentation - Detailed Explanation

---

## Slide 1: Problem Statement

### Why do we need Spark Streaming?

**Problems with current Consumer:**
- ❌ Process messages individually, not synchronized
- ❌ Only keep latest value (overwrites)
- ❌ No feature calculation (mean, std, min, max)
- ❌ Cannot create training dataset
- ❌ No real-time anomaly detection

**Solution: Spark Streaming**
- ✅ Synchronize 17 sensors by time window
- ✅ Calculate features real-time (statistics, aggregations)
- ✅ Detect anomalies immediately
- ✅ Write processed data to HDFS
- ✅ Automatically create training dataset

---

## Slide 2: What is Spark Streaming?

### Apache Spark Structured Streaming

**Definition:**
- Real-time data processing framework from Apache Spark
- Process streaming data like batch processing
- Automatically manages state, checkpointing, recovery

**Features:**
- **Unified API:** Same API as Spark SQL
- **Fault-tolerant:** Auto-recover on failure
- **Scalable:** Process millions of messages/second
- **Exactly-once:** Ensure each message processed only once

**Comparison with current Consumer:**

| Feature | Python Consumer | Spark Streaming |
|---------|----------------|-----------------|
| Processing | Sequential, individual | Batch, window-based |
| Synchronization | No | Yes (time window) |
| Features | No | Yes (built-in) |
| Fault-tolerant | No | Yes (checkpoint) |
| Scale | 1 process | Distributed |

---

## Slide 3: Spark Streaming Architecture

### Data Flow

```
┌──────────────────┐
│  Kafka           │  17 topics (hydraulic-PS1, PS2, ..., SE)
│  (17 topics)     │  Messages arrive asynchronously
└────────┬─────────┘
         │
         │ Spark Structured Streaming
         │ (subscribe all topics)
         ▼
┌─────────────────────────────┐
│  Spark Streaming App        │
│  - Window: 1 second         │  ← Synchronization
│  - Join 17 sensors          │  ← Group messages
│  - Calculate features       │  ← Statistics
│  - Detect anomalies         │  ← Real-time alerts
└────────┬────────────────────┘
         │
         ├─────────────────┬──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
    ┌──────────┐    ┌──────────┐      ┌──────────┐
    │ HDFS     │    │ Console  │      │ Kafka    │
    │ (Parquet)│    │ (logs)   │      │ (alerts) │
    └──────────┘    └──────────┘      └──────────┘
```

**Explanation:**
1. **Kafka:** 17 topics, messages arrive asynchronously
2. **Spark Streaming:** Subscribe all topics, process by window
3. **Processing:** Synchronize, calculate features, detect anomalies
4. **Output:** Write to HDFS, console, or Kafka alerts

---

## Slide 4: Window-based Processing

### How to Synchronize Sensors

**Problem:**
- PS1 (100Hz): 100 messages/second
- FS1 (10Hz): 10 messages/second
- TS1 (1Hz): 1 message/second
- Messages arrive asynchronously

**Solution: Time Window**

```
Time Window: 1 second (14:30:45 - 14:30:46)

Messages in window:
- PS1: 100 messages (0.00s, 0.01s, ..., 0.99s)
- FS1: 10 messages (0.0s, 0.1s, ..., 0.9s)
- TS1: 1 message (0.0s)

Spark processing:
1. Group all messages in window
2. Aggregate by sensor:
   - PS1: avg, min, max, std of 100 values
   - FS1: avg, min, max, std of 10 values
   - TS1: avg, min, max, std of 1 value
3. Join all sensors together
4. Create 1 record per second
```

**Result:**
- Each second = 1 record with all 17 sensors
- Fully synchronized
- Can calculate features

---

## Slide 5: Feature Calculation

### Statistical Features

**From synchronized data, Spark calculates:**

**1. Basic Statistics:**
```python
- Average (mean): Mean value
- Min: Minimum value
- Max: Maximum value
- Standard deviation: Standard deviation
- Count: Number of samples
```

**2. Aggregated Features:**
```python
- Pressure mean: (PS1 + PS2 + ... + PS6) / 6
- Temperature mean: (TS1 + TS2 + TS3 + TS4) / 4
- Flow mean: (FS1 + FS2) / 2
```

**3. Derived Features:**
```python
- Pressure range: max - min
- Pressure variability: std / mean
- Flow-pressure ratio: flow / pressure
- Efficiency index: SE × CE / 100
```

**Example:**
```
Window: 14:30:45 - 14:30:46

PS1: [151.19, 152.33, ..., 153.45] (100 values)
  → avg = 152.5, min = 151.19, max = 153.45, std = 0.8

FS1: [12.5, 12.6, ..., 12.9] (10 values)
  → avg = 12.7, min = 12.5, max = 12.9, std = 0.1

TS1: [45.2] (1 value)
  → avg = 45.2, min = 45.2, max = 45.2, std = 0.0

Features:
  → pressure_mean = (PS1_avg + PS2_avg + ... + PS6_avg) / 6
  → temperature_mean = (TS1_avg + TS2_avg + TS3_avg + TS4_avg) / 4
```

---

## Slide 6: Anomaly Detection

### Real-time Fault Detection

**Spark Streaming can detect:**

**1. Threshold-based:**
```python
- High pressure: PS1 > 300 bar
- High temperature: TS1 > 100°C
- Pressure spike: pressure_range > 50 bar
```

**2. Statistical Outliers:**
```python
- Z-score > 3: Value deviates too far from mean
- Sudden change: Rate of change > threshold
```

**3. Pattern Matching:**
```python
- Unusual patterns: Compare with normal patterns
- Cross-sensor anomalies: Abnormal correlations
```

**Example:**
```
Window: 14:30:45

PS1_avg = 350.0 bar  ← Exceeds threshold (300 bar)
TS1_avg = 45.2°C     ← Normal
pressure_range = 60.0 bar  ← Exceeds threshold (50 bar)

→ Detected: "high_pressure" anomaly
→ Alert: Send to Kafka alerts topic
→ Log: Write to console
```

---

## Slide 7: Setup Process

### Installation Steps

**Step 1: Download Spark**
```bash
# Download Spark 3.5.0
wget https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz

# Extract
tar -xzf spark-3.5.0-bin-hadoop3.tgz

# Set environment
export SPARK_HOME=$(pwd)/spark-3.5.0-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin
```

**Step 2: Configuration**
```bash
# Create config file
$SPARK_HOME/conf/spark-defaults.conf

# Configure:
- Memory settings
- Kafka integration
- Checkpoint location
```

**Step 3: Install Dependencies**
```bash
pip install pyspark>=3.3.0
```

**Step 4: Run Application**
```bash
$SPARK_HOME/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  src/spark_streaming_app.py
```

---

## Slide 8: Code Structure

### Spark Streaming App Structure

**1. Create SparkSession:**
```python
spark = SparkSession.builder \
    .appName("HydraulicSystemStreaming") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints") \
    .getOrCreate()
```

**2. Read from Kafka:**
```python
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:29092") \
    .option("subscribe", "hydraulic-PS1,hydraulic-PS2,...") \
    .load()
```

**3. Parse Messages:**
```python
df_parsed = df.select(
    from_json(col("value").cast("string"), schema).alias("data")
)
```

**4. Window Aggregation:**
```python
df_windowed = df_parsed \
    .withWatermark("timestamp", "10 seconds") \
    .groupBy(
        window("timestamp", "1 second"),
        "cycle",
        "sensor"
    ) \
    .agg(avg("value"), min("value"), max("value"), ...)
```

**5. Write to HDFS:**
```python
query = df_windowed.writeStream \
    .format("parquet") \
    .option("path", "hdfs://localhost:9000/hydraulic_data/") \
    .start()
```

---

## Slide 9: Window & Watermark

### Time Window and Watermark

**Time Window:**
- **Window duration:** 1 second
- **Slide interval:** 1 second (non-overlapping)
- **Purpose:** Group messages in the same second

**Watermark:**
- **Purpose:** Handle late data (messages arriving late)
- **Value:** 10 seconds
- **Meaning:** Accept messages up to 10 seconds late

**Example:**
```
Current time: 14:30:50

Window: 14:30:45 - 14:30:46
  - Messages on time: Process immediately
  - Messages late (within 10s): Still process
  - Messages too late (>10s): Ignore

Watermark = 14:30:40 (14:30:50 - 10s)
  - Only process windows >= watermark
```

**Benefits:**
- Can handle late data
- Ensure accuracy
- Automatically cleanup old data

---

## Slide 10: Join Multiple Sensors

### How to Join 17 Sensors

**Problem:**
- Spark Streaming doesn't support direct join of multiple streams
- Need different approach

**Solution 1: Pivot**
```python
# Pivot to have each sensor as a column
df_pivoted = df_parsed \
    .groupBy(window("timestamp", "1 second"), "cycle") \
    .pivot("sensor") \
    .agg(avg("value").alias("avg"))

# Result:
# window | cycle | PS1_avg | PS2_avg | ... | TS1_avg | ...
```

**Solution 2: Union All + GroupBy**
```python
# Union all sensors
df_all = df_ps1.union(df_ps2).union(...).union(df_se)

# GroupBy and pivot
df_joined = df_all \
    .groupBy("window", "cycle") \
    .pivot("sensor") \
    .agg(avg("value"))
```

**Result:**
- 1 record/second with all 17 sensors
- Each sensor is a column
- Easy to calculate features

---

## Slide 11: Write to HDFS

### Store Processed Data

**Directory structure:**
```
hdfs://localhost:9000/hydraulic_data/
  /streaming/
    /year=2025/
      /month=11/
        /day=08/
          /hour=14/
            /minute=30/
              /second=45/
                /cycle=0/
                  part-00000.parquet
```

**Code:**
```python
# Add partition columns
df_partitioned = df \
    .withColumn("year", year("window_start")) \
    .withColumn("month", month("window_start")) \
    .withColumn("day", dayofmonth("window_start")) \
    .withColumn("hour", hour("window_start")) \
    .withColumn("minute", minute("window_start")) \
    .withColumn("second", second("window_start"))

# Write to HDFS
query = df_partitioned.writeStream \
    .format("parquet") \
    .option("path", "hdfs://localhost:9000/hydraulic_data/streaming") \
    .partitionBy("year", "month", "day", "hour", "minute", "second", "cycle") \
    .start()
```

**Benefits:**
- Partition by time → Fast queries
- Parquet format → Compressed, columnar
- Easy to create training dataset later

---

## Slide 12: Monitoring & Debugging

### Spark UI

**Access:**
```
http://localhost:4040
```

**Can view:**
- **Streaming Queries:** List of running queries
- **Jobs:** Details of each job
- **Stages:** Stages in job
- **Metrics:** Throughput, latency, records processed
- **Query Progress:** Progress of streaming queries

**Important metrics:**
- **Input Rate:** Messages/second read from Kafka
- **Processing Rate:** Records/second processed
- **Batch Duration:** Time to process each batch
- **Records:** Number of records processed

**Debug:**
- View logs in Spark UI
- Check query status
- Monitor lag (if any)

---

## Slide 13: Use Cases

### Real-world Applications

**1. Real-time Monitoring:**
- Display features real-time on dashboard
- Compare with thresholds
- Alert on anomalies

**2. Feature Engineering:**
- Automatically calculate features
- Store in HDFS
- Use for ML models

**3. Anomaly Detection:**
- Detect faults immediately
- Send alerts
- Log to database

**4. Training Dataset:**
- Aggregate 60 seconds → 1 cycle
- Join with labels
- Export for ML training

**5. Historical Analysis:**
- Query data from HDFS
- Analyze trends
- Compare cycles

---

## Slide 14: Comparison with Current Consumer

### Python Consumer vs Spark Streaming

| Feature | Python Consumer | Spark Streaming |
|---------|----------------|-----------------|
| **Processing** | Sequential, individual | Batch, window-based |
| **Synchronization** | ❌ No | ✅ Yes (time window) |
| **Features** | ❌ No | ✅ Yes (built-in) |
| **Fault-tolerant** | ❌ No | ✅ Yes (checkpoint) |
| **Scale** | 1 process | Distributed |
| **Memory** | Keep latest value | Keep all in window |
| **Output** | Prometheus only | HDFS, Console, Kafka |
| **Anomaly Detection** | ❌ No | ✅ Yes |
| **Training Dataset** | ❌ No | ✅ Yes |

**When to use what:**
- **Python Consumer:** Simple real-time monitoring
- **Spark Streaming:** Complex processing, features, training dataset

---

## Slide 15: Performance

### Throughput & Latency

**Throughput:**
- **Input:** ~43,680 messages/second (1 cycle)
- **Processing:** Spark can process millions of messages/second
- **Output:** 1 record/second (after aggregation)

**Latency:**
- **Window:** 1 second
- **Processing:** < 100ms (typically)
- **End-to-end:** ~1-2 seconds (from Kafka → HDFS)

**Resource Usage:**
- **Memory:** ~2-4GB (depending on window size)
- **CPU:** 2+ cores
- **Disk:** Checkpoint location (~100MB-1GB)

**Optimization:**
- Increase parallelism
- Optimize window size
- Compression (Parquet)
- Partitioning

---

## Slide 16: Checkpointing & Recovery

### Fault Tolerance

**Checkpointing:**
- **Location:** `/tmp/spark-checkpoints`
- **Purpose:** Save state for recovery
- **Frequency:** Every batch

**Recovery:**
- If Spark crashes → Restart
- Automatically read from checkpoint
- Continue from where it stopped
- No data loss

**Checkpoint contains:**
- Source offsets (Kafka)
- Sink state (HDFS)
- Metadata
- Progress

**Best Practice:**
- Always enable checkpoint
- Backup checkpoint location
- Monitor checkpoint size

---

## Slide 17: Integration with HDFS

### Create Training Dataset

**Data flow:**
```
Spark Streaming → HDFS (1 second/record)
         ↓
Spark Batch Job (read from HDFS)
         ↓
Aggregate 60 seconds → 1 cycle
         ↓
Join with labels (profile.txt)
         ↓
Training Dataset (Parquet/CSV)
```

**Example:**
```
HDFS: 60 files (1 file/second)
  → 14:30:00 → 14:30:01: data.parquet
  → 14:30:01 → 14:30:02: data.parquet
  ...
  → 14:30:59 → 14:31:00: data.parquet

Spark Batch:
  → Read 60 files
  → Aggregate into 1 record
  → Join with labels
  → Export training dataset
```

**Benefits:**
- Automatically create training dataset
- Labels ready
- Easy feature engineering
- Suitable for ML pipeline

---

## Slide 18: Troubleshooting

### Common Issues

**1. Kafka Connection Failed**
```bash
# Check Kafka
docker ps | grep kafka

# Test connection
kafka-console-consumer.sh --bootstrap-server localhost:29092 --topic hydraulic-PS1
```

**2. Out of Memory**
```properties
# Increase memory in spark-defaults.conf
spark.driver.memory 4g
spark.executor.memory 4g
```

**3. Checkpoint Issues**
```bash
# Create checkpoint directory
mkdir -p /tmp/spark-checkpoints
chmod 777 /tmp/spark-checkpoints
```

**4. Schema Mismatch**
- Check message format from producer
- Verify schema matches actual data
- Check JSON parsing

**5. Slow Processing**
- Increase parallelism
- Optimize window size
- Check network latency
- Monitor resource usage

---

## Slide 19: Best Practices

### Recommendations

**1. Watermark:**
- Always use watermark to handle late data
- Set watermark = 2-3x window duration

**2. Checkpointing:**
- Enable checkpoint for recovery
- Backup checkpoint location
- Monitor checkpoint size

**3. Partitioning:**
- Partition by time for fast queries
- Use appropriate partition columns

**4. Monitoring:**
- Monitor Spark UI
- Check query progress
- Monitor lag

**5. Testing:**
- Test with console output first
- Test with 1-2 sensors first
- Scale to 17 sensors later

**6. Optimization:**
- Optimize window size
- Use compression (Parquet)
- Increase parallelism if needed

---

## Slide 20: Summary

### Key Points

**Spark Streaming:**
- ✅ Synchronize 17 sensors by time window
- ✅ Calculate features real-time
- ✅ Detect anomalies
- ✅ Write to HDFS
- ✅ Create training dataset

**Compared to current Consumer:**
- ✅ Better processing (window-based)
- ✅ Feature calculation
- ✅ Fault-tolerant
- ✅ Scalable

**Use Cases:**
- ✅ Real-time monitoring with features
- ✅ Anomaly detection
- ✅ Training dataset generation
- ✅ Historical analysis

**Next Steps:**
1. Setup Spark Streaming
2. Test with 1-2 sensors
3. Scale to 17 sensors
4. Integrate with HDFS
5. Create training dataset

---

## Slide 21: References

### Documentation

1. **Spark Documentation:**
   - [Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
   - [Kafka Integration](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)

2. **Project Documentation:**
   - `docs/SPARK_STREAMING_SETUP.md` - Detailed setup guide
   - `docs/HDFS_SETUP.md` - HDFS integration
   - `docs/ARCHITECTURE.md` - System architecture

3. **Code:**
   - `src/spark_streaming_app.py` - Spark Streaming application
   - `src/consumer.py` - Python consumer (for comparison)

---

## Slide 22: Q&A

### Frequently Asked Questions

**Q1: Why not use Python Consumer?**
A: Python Consumer processes individually, not synchronized, no features. Spark Streaming processes better.

**Q2: Is Spark Streaming slow?**
A: No, Spark is very fast. Latency ~1-2 seconds, throughput millions of messages/second.

**Q3: Can we use Spark Streaming instead of Python Consumer?**
A: Yes, but Python Consumer is simpler for basic monitoring. Spark Streaming for complex processing.

**Q4: How much resources needed?**
A: Minimum 4GB RAM, 2 cores. Recommended 8GB+ RAM, 4+ cores.

**Q5: How to know if Spark Streaming works correctly?**
A: Check Spark UI (localhost:4040), view metrics, verify data in HDFS.

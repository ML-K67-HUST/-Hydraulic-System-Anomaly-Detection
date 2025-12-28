# 🚀 Spark Streaming Setup Guide
## Real-time Data Processing với Spark Structured Streaming

Hướng dẫn chi tiết setup và sử dụng Spark Streaming để xử lý dữ liệu real-time từ Kafka, đồng bộ hóa 17 sensors, và tính toán features.

---

## 📋 Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Yêu Cầu Hệ Thống](#2-yêu-cầu-hệ-thống)
3. [Cài Đặt Spark](#3-cài-đặt-spark)
4. [Cấu Hình Kafka Consumer](#4-cấu-hình-kafka-consumer)
5. [Spark Streaming Application](#5-spark-streaming-application)
6. [Đồng Bộ Hóa 17 Sensors](#6-đồng-bộ-hóa-17-sensors)
7. [Tính Toán Features](#7-tính-toán-features)
8. [Ghi Dữ Liệu Vào HDFS](#8-ghi-dữ-liệu-vào-hdfs)
9. [Monitoring & Debugging](#9-monitoring--debugging)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Tổng Quan

### 1.1. Mục Đích

Spark Streaming được dùng để:
- ✅ Đọc dữ liệu real-time từ 17 Kafka topics
- ✅ Đồng bộ hóa messages từ các sensors với tốc độ khác nhau
- ✅ Tính toán features real-time (aggregation, statistics)
- ✅ Phát hiện anomalies
- ✅ Ghi dữ liệu đã xử lý vào HDFS

### 1.2. Kiến Trúc

```
┌──────────────────┐
│  Kafka           │  17 topics (hydraulic-PS1, PS2, ..., SE)
│  (17 topics)     │
└────────┬─────────┘
         │
         │ Spark Structured Streaming
         │ (subscribe all topics)
         ▼
┌─────────────────────────────┐
│  Spark Streaming App        │
│  - Window: 1 second         │
│  - Join 17 sensors          │
│  - Calculate features       │
│  - Detect anomalies         │
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

### 1.3. Luồng Dữ Liệu

1. **Producer** gửi messages vào 17 Kafka topics
2. **Spark Streaming** subscribe tất cả topics
3. **Window-based processing** (1 giây) để đồng bộ hóa
4. **Join & Aggregate** messages từ 17 sensors
5. **Calculate features** (mean, std, min, max, etc.)
6. **Write to HDFS** (Parquet format)

---

## 2. Yêu Cầu Hệ Thống

### 2.1. Phần Mềm

- **Java 8 hoặc 11** (required for Spark)
- **Python 3.8+** (cho PySpark)
- **Apache Spark 3.3.0+**
- **Kafka** (đã có trong project)
- **HDFS** (sẽ setup sau)

### 2.2. Tài Nguyên

- **RAM:** Tối thiểu 4GB (khuyến nghị 8GB+)
- **CPU:** 2+ cores
- **Disk:** 10GB+ free space

### 2.3. Dependencies

Cần thêm vào `requirements.txt`:
```
pyspark>=3.3.0
kafka-python>=2.0.2
```

---

## 3. Cài Đặt Spark

### 3.1. Download Spark

```bash
# Tạo thư mục cho Spark
mkdir -p ~/spark
cd ~/spark

# Download Spark 3.5.0 (hoặc version mới nhất)
wget https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz

# Giải nén
tar -xzf spark-3.5.0-bin-hadoop3.tgz
cd spark-3.5.0-bin-hadoop3

# Set environment variables
export SPARK_HOME=$(pwd)
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
```

### 3.2. Cấu Hình Spark

Tạo file `$SPARK_HOME/conf/spark-defaults.conf`:

```properties
# Spark configuration
spark.master                     local[2]
spark.app.name                   HydraulicSystemStreaming
spark.sql.streaming.checkpointLocation /tmp/spark-checkpoints
spark.sql.streaming.schemaInference true

# Kafka integration
spark.jars.packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0

# Memory settings
spark.driver.memory              2g
spark.executor.memory            2g
spark.driver.maxResultSize       1g

# Streaming settings
spark.sql.streaming.stopGracefullyOnShutdown true
spark.sql.streaming.streamingQueryListeners org.apache.spark.sql.streaming.StreamingQueryListener
```

### 3.3. Verify Installation

```bash
# Kiểm tra Spark
$SPARK_HOME/bin/spark-submit --version

# Chạy PySpark shell để test
$SPARK_HOME/bin/pyspark
```

Trong PySpark shell:
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("Test").getOrCreate()
print(spark.version)  # Should print 3.5.0
```

---

## 4. Cấu Hình Kafka Consumer

### 4.1. Kafka Topics

Đảm bảo 17 topics đã được tạo:

```bash
# List topics
kafka-topics.sh --bootstrap-server localhost:29092 --list

# Nếu chưa có, tạo topics:
kafka-topics.sh --bootstrap-server localhost:29092 --create --topic hydraulic-PS1 --partitions 1 --replication-factor 1
# ... (tạo cho tất cả 17 topics)
```

Hoặc dùng script có sẵn:
```bash
cd scripts
python create_kafka_topics.py
```

### 4.2. Kafka Consumer Group

Spark sẽ tự động tạo consumer group. Có thể monitor:

```bash
# Xem consumer groups
kafka-consumer-groups.sh --bootstrap-server localhost:29092 --list

# Xem lag
kafka-consumer-groups.sh --bootstrap-server localhost:29092 \
  --group spark-streaming-group --describe
```

---

## 5. Spark Streaming Application

### 5.1. Tạo Spark Streaming App

Tạo file `src/spark_streaming_app.py`:

```python
#!/usr/bin/env python3
"""
Spark Structured Streaming Application
Đọc dữ liệu từ 17 Kafka topics, đồng bộ hóa và tính toán features
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
from datetime import datetime

# Kafka configuration
KAFKA_BROKER = "localhost:29092"
SENSOR_TOPICS = [
    "hydraulic-PS1", "hydraulic-PS2", "hydraulic-PS3",
    "hydraulic-PS4", "hydraulic-PS5", "hydraulic-PS6",
    "hydraulic-EPS1",
    "hydraulic-FS1", "hydraulic-FS2",
    "hydraulic-TS1", "hydraulic-TS2", "hydraulic-TS3", "hydraulic-TS4",
    "hydraulic-CE", "hydraulic-CP", "hydraulic-SE", "hydraulic-VS1"
]

# Schema cho Kafka messages
MESSAGE_SCHEMA = StructType([
    StructField("sensor", StringType(), True),
    StructField("cycle", IntegerType(), True),
    StructField("sample_idx", IntegerType(), True),
    StructField("value", DoubleType(), True),
    StructField("timestamp", StringType(), True),
    StructField("sampling_rate_hz", IntegerType(), True)
])


def create_spark_session():
    """Tạo SparkSession với cấu hình phù hợp"""
    spark = SparkSession.builder \
        .appName("HydraulicSystemStreaming") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


def read_kafka_stream(spark, topic):
    """Đọc stream từ 1 Kafka topic"""
    return spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()


def parse_kafka_message(df):
    """Parse JSON messages từ Kafka"""
    # Parse value column (JSON string)
    df_parsed = df.select(
        col("key").cast("string"),
        from_json(col("value").cast("string"), MESSAGE_SCHEMA).alias("data"),
        col("timestamp").alias("kafka_timestamp")
    )
    
    # Flatten nested structure
    df_flattened = df_parsed.select(
        col("data.sensor").alias("sensor"),
        col("data.cycle").alias("cycle"),
        col("data.sample_idx").alias("sample_idx"),
        col("data.value").alias("value"),
        to_timestamp(col("data.timestamp")).alias("event_timestamp"),
        col("data.sampling_rate_hz").alias("sampling_rate_hz"),
        col("kafka_timestamp")
    )
    
    return df_flattened


def aggregate_by_window(df, window_duration="1 second"):
    """Aggregate messages theo time window"""
    windowed = df \
        .withWatermark("event_timestamp", "10 seconds") \
        .groupBy(
            window("event_timestamp", window_duration),
            "cycle",
            "sensor"
        ) \
        .agg(
            collect_list("value").alias("values"),
            count("value").alias("count"),
            avg("value").alias("avg_value"),
            min("value").alias("min_value"),
            max("value").alias("max_value"),
            stddev("value").alias("std_value"),
            first("sample_idx").alias("first_sample_idx"),
            last("sample_idx").alias("last_sample_idx")
        )
    
    return windowed


def join_all_sensors(sensor_dfs):
    """Join tất cả sensors lại với nhau theo time window"""
    # Start với sensor đầu tiên
    result = sensor_dfs[0]
    
    # Join với các sensors còn lại
    for i in range(1, len(sensor_dfs)):
        result = result.join(
            sensor_dfs[i],
            ["window", "cycle"],
            "outer"
        )
    
    return result


def calculate_features(df):
    """Tính toán features từ dữ liệu đã join"""
    # Thêm các features mới
    df_features = df \
        .withColumn("window_start", col("window.start")) \
        .withColumn("window_end", col("window.end")) \
        .withColumn("pressure_avg", 
            (col("PS1_avg_value") + col("PS2_avg_value") + 
             col("PS3_avg_value") + col("PS4_avg_value") + 
             col("PS5_avg_value") + col("PS6_avg_value")) / 6
        ) \
        .withColumn("pressure_range",
            col("PS1_max_value") - col("PS1_min_value")
        ) \
        .withColumn("temperature_avg",
            (col("TS1_avg_value") + col("TS2_avg_value") + 
             col("TS3_avg_value") + col("TS4_avg_value")) / 4
        )
    
    return df_features


def detect_anomalies(df):
    """Phát hiện anomalies dựa trên thresholds"""
    # Define thresholds
    PRESSURE_MAX = 300.0  # bar
    TEMPERATURE_MAX = 100.0  # °C
    
    anomalies = df \
        .filter(
            (col("PS1_avg_value") > PRESSURE_MAX) |
            (col("temperature_avg") > TEMPERATURE_MAX) |
            (col("pressure_range") > 50.0)
        ) \
        .withColumn("anomaly_type", 
            when(col("PS1_avg_value") > PRESSURE_MAX, "high_pressure")
            .when(col("temperature_avg") > TEMPERATURE_MAX, "high_temperature")
            .otherwise("pressure_range_anomaly")
        )
    
    return anomalies


def write_to_hdfs(df, output_path, format="parquet"):
    """Ghi dữ liệu vào HDFS"""
    query = df \
        .writeStream \
        .format(format) \
        .option("path", output_path) \
        .option("checkpointLocation", f"/tmp/spark-checkpoints/hdfs") \
        .partitionBy("cycle", "year", "month", "day", "hour", "minute") \
        .outputMode("append") \
        .trigger(processingTime="1 second") \
        .start()
    
    return query


def write_to_console(df):
    """Ghi dữ liệu ra console để debug"""
    query = df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="5 seconds") \
        .start()
    
    return query


def main():
    """Main function"""
    print("=" * 80)
    print("🚀 Spark Streaming Application - Hydraulic System")
    print("=" * 80)
    
    # Tạo SparkSession
    spark = create_spark_session()
    
    print(f"✅ Spark version: {spark.version}")
    print(f"✅ Kafka broker: {KAFKA_BROKER}")
    print(f"✅ Topics: {len(SENSOR_TOPICS)}")
    
    # Đọc streams từ tất cả topics
    print("\n📊 Reading streams from Kafka topics...")
    sensor_streams = {}
    
    for topic in SENSOR_TOPICS:
        print(f"  - Reading {topic}...")
        df_raw = read_kafka_stream(spark, topic)
        df_parsed = parse_kafka_message(df_raw)
        df_aggregated = aggregate_by_window(df_parsed)
        
        # Rename columns với prefix sensor name
        sensor_name = topic.replace("hydraulic-", "")
        df_renamed = df_aggregated.select(
            col("window"),
            col("cycle"),
            col(f"{sensor_name}_values").alias(f"{sensor_name}_values"),
            col("count").alias(f"{sensor_name}_count"),
            col("avg_value").alias(f"{sensor_name}_avg_value"),
            col("min_value").alias(f"{sensor_name}_min_value"),
            col("max_value").alias(f"{sensor_name}_max_value"),
            col("std_value").alias(f"{sensor_name}_std_value")
        )
        
        sensor_streams[sensor_name] = df_renamed
    
    # Join tất cả sensors
    print("\n🔗 Joining all sensors...")
    # Note: Spark Streaming không support join trực tiếp nhiều streams
    # Cần dùng approach khác (xem phần sau)
    
    # Tạm thời xử lý từng sensor riêng
    print("\n💾 Writing to HDFS...")
    queries = []
    
    for sensor_name, df in sensor_streams.items():
        output_path = f"hdfs://localhost:9000/hydraulic_data/streaming/{sensor_name}"
        query = write_to_hdfs(df, output_path)
        queries.append(query)
        print(f"  ✅ Started query for {sensor_name}")
    
    # Hoặc ghi ra console để test
    print("\n📺 Writing to console (for testing)...")
    test_query = write_to_console(sensor_streams["PS1"])
    queries.append(test_query)
    
    # Chờ queries
    print("\n⏳ Waiting for streaming queries...")
    print("Press Ctrl+C to stop\n")
    
    try:
        for query in queries:
            query.awaitTermination()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping streaming queries...")
        for query in queries:
            query.stop()
        
        print("✅ All queries stopped")
        spark.stop()


if __name__ == "__main__":
    main()
```

### 5.2. Chạy Spark Streaming App

```bash
# Chạy với spark-submit
$SPARK_HOME/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --master local[2] \
  src/spark_streaming_app.py
```

---

## 6. Đồng Bộ Hóa 17 Sensors

### 6.1. Vấn Đề

Messages từ 17 sensors đến không đồng bộ:
- PS1 (100Hz): 100 messages/giây
- FS1 (10Hz): 10 messages/giây
- TS1 (1Hz): 1 message/giây

### 6.2. Giải Pháp: Window-based Aggregation

```python
def synchronize_sensors(spark):
    """Đồng bộ hóa tất cả sensors bằng window"""
    
    # Đọc tất cả topics cùng lúc
    df_all = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", ",".join(SENSOR_TOPICS)) \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse messages
    df_parsed = parse_kafka_message(df_all)
    
    # Pivot để có mỗi sensor là 1 column
    df_pivoted = df_parsed \
        .withWatermark("event_timestamp", "10 seconds") \
        .groupBy(
            window("event_timestamp", "1 second"),
            "cycle"
        ) \
        .pivot("sensor") \
        .agg(
            collect_list("value").alias("values"),
            avg("value").alias("avg"),
            min("value").alias("min"),
            max("value").alias("max")
        )
    
    return df_pivoted
```

### 6.3. Interpolation cho Sensors Chậm

```python
def interpolate_slow_sensors(df):
    """Interpolate sensors chậm (1Hz, 10Hz) để match với 100Hz"""
    from pyspark.sql.window import Window
    
    # Forward fill cho sensors chậm
    window_spec = Window \
        .partitionBy("cycle") \
        .orderBy("window") \
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    df_interpolated = df \
        .withColumn("TS1_interpolated", 
            last("TS1_avg", ignorenulls=True).over(window_spec)
        ) \
        .withColumn("FS1_interpolated",
            last("FS1_avg", ignorenulls=True).over(window_spec)
        )
    
    return df_interpolated
```

---

## 7. Tính Toán Features

### 7.1. Statistical Features

```python
def calculate_statistical_features(df):
    """Tính toán statistical features"""
    df_features = df \
        .withColumn("pressure_mean", 
            (col("PS1_avg") + col("PS2_avg") + col("PS3_avg") + 
             col("PS4_avg") + col("PS5_avg") + col("PS6_avg")) / 6
        ) \
        .withColumn("pressure_std",
            sqrt(
                (col("PS1_std")**2 + col("PS2_std")**2 + 
                 col("PS3_std")**2 + col("PS4_std")**2 + 
                 col("PS5_std")**2 + col("PS6_std")**2) / 6
            )
        ) \
        .withColumn("temperature_mean",
            (col("TS1_avg") + col("TS2_avg") + 
             col("TS3_avg") + col("TS4_avg")) / 4
        ) \
        .withColumn("flow_mean",
            (col("FS1_avg") + col("FS2_avg")) / 2
        )
    
    return df_features
```

### 7.2. Time-domain Features

```python
def calculate_time_domain_features(df):
    """Tính toán time-domain features"""
    from pyspark.sql.window import Window
    
    window_spec = Window \
        .partitionBy("cycle") \
        .orderBy("window") \
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    df_time_features = df \
        .withColumn("pressure_rate_of_change",
            (col("pressure_mean") - 
             lag("pressure_mean", 1).over(window_spec)) / 1.0
        ) \
        .withColumn("pressure_rolling_mean",
            avg("pressure_mean").over(
                window_spec.rowsBetween(-5, Window.currentRow)
            )
        )
    
    return df_time_features
```

### 7.3. Cross-sensor Features

```python
def calculate_cross_sensor_features(df):
    """Tính toán features giữa các sensors"""
    df_cross = df \
        .withColumn("pressure_temperature_ratio",
            col("pressure_mean") / (col("temperature_mean") + 1e-6)
        ) \
        .withColumn("flow_pressure_product",
            col("flow_mean") * col("pressure_mean")
        ) \
        .withColumn("efficiency_index",
            col("SE_avg") * col("CE_avg") / 100.0
        )
    
    return df_cross
```

---

## 8. Ghi Dữ Liệu Vào HDFS

### 8.1. Cấu Trúc Thư Mục

```
hdfs://localhost:9000/hydraulic_data/
  /streaming/
    /year=2025/
      /month=11/
        /day=08/
          /hour=14/
            /minute=30/
              /second=45/
                part-00000.parquet
```

### 8.2. Code Ghi Vào HDFS

```python
def write_to_hdfs_with_partitioning(df, base_path):
    """Ghi vào HDFS với partitioning theo thời gian"""
    
    # Thêm partition columns
    df_partitioned = df \
        .withColumn("year", year("window_start")) \
        .withColumn("month", month("window_start")) \
        .withColumn("day", dayofmonth("window_start")) \
        .withColumn("hour", hour("window_start")) \
        .withColumn("minute", minute("window_start")) \
        .withColumn("second", second("window_start"))
    
    # Ghi vào HDFS
    query = df_partitioned \
        .writeStream \
        .format("parquet") \
        .option("path", base_path) \
        .option("checkpointLocation", "/tmp/spark-checkpoints/hdfs") \
        .partitionBy("year", "month", "day", "hour", "minute", "second", "cycle") \
        .outputMode("append") \
        .trigger(processingTime="1 second") \
        .start()
    
    return query
```

### 8.3. Verify Data in HDFS

```bash
# List files
hdfs dfs -ls -R /hydraulic_data/streaming/

# Read sample data
hdfs dfs -cat /hydraulic_data/streaming/year=2025/month=11/day=08/hour=14/minute=30/second=45/part-00000.parquet | head
```

---

## 9. Monitoring & Debugging

### 9.1. Spark UI

Truy cập Spark UI:
```
http://localhost:4040
```

Xem:
- Streaming queries
- Jobs & stages
- Metrics
- Query progress

### 9.2. Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Trong code
logger.info(f"Processing {df.count()} records")
```

### 9.3. Metrics

```python
def monitor_query(query):
    """Monitor streaming query"""
    while query.isActive:
        print(f"Status: {query.status}")
        print(f"Recent progress: {query.recentProgress}")
        time.sleep(5)
```

---

## 10. Troubleshooting

### 10.1. Kafka Connection Issues

**Lỗi:** `Failed to connect to Kafka`

**Giải pháp:**
```bash
# Kiểm tra Kafka đang chạy
docker ps | grep kafka

# Test connection
kafka-console-consumer.sh --bootstrap-server localhost:29092 --topic hydraulic-PS1 --from-beginning
```

### 10.2. Memory Issues

**Lỗi:** `OutOfMemoryError`

**Giải pháp:**
- Tăng memory trong `spark-defaults.conf`:
```properties
spark.driver.memory 4g
spark.executor.memory 4g
```

### 10.3. Checkpoint Issues

**Lỗi:** `Checkpoint directory not found`

**Giải pháp:**
```bash
# Tạo checkpoint directory
mkdir -p /tmp/spark-checkpoints
chmod 777 /tmp/spark-checkpoints
```

### 10.4. Schema Mismatch

**Lỗi:** `Schema mismatch`

**Giải pháp:**
- Kiểm tra message format từ producer
- Verify MESSAGE_SCHEMA matches actual data

---

## 11. Best Practices

1. **Watermark:** Luôn dùng watermark để xử lý late data
2. **Checkpointing:** Enable checkpoint để recovery
3. **Partitioning:** Partition theo thời gian để query nhanh
4. **Monitoring:** Monitor Spark UI và logs
5. **Testing:** Test với console output trước khi ghi HDFS

---

## 12. Next Steps

Sau khi setup Spark Streaming:
1. ✅ Verify data flow
2. ✅ Test với 1-2 sensors trước
3. ✅ Scale lên 17 sensors
4. ✅ Tối ưu performance
5. ✅ Setup monitoring alerts

---

## 📚 References

- [Spark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Kafka Integration](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)
- [HDFS Integration](https://spark.apache.org/docs/latest/sql-data-sources-parquet.html)


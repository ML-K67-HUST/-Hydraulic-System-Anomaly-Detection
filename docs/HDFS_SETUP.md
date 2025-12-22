# 💾 HDFS Setup Guide
## Distributed Storage cho Batch Processing và Training Dataset

Hướng dẫn chi tiết setup HDFS để lưu trữ dữ liệu batch, tạo training dataset từ dữ liệu đã gom, và join với labels.

---

## 📋 Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Yêu Cầu Hệ Thống](#2-yêu-cầu-hệ-thống)
3. [Cài Đặt HDFS](#3-cài-đặt-hdfs)
4. [Cấu Hình HDFS](#4-cấu-hình-hdfs)
5. [Cấu Trúc Dữ Liệu](#5-cấu-trúc-dữ-liệu)
6. [Ghi Dữ Liệu Vào HDFS](#6-ghi-dữ-liệu-vào-hdfs)
7. [Đọc Dữ Liệu Từ HDFS](#7-đọc-dữ-liệu-từ-hdfs)
8. [Tạo Training Dataset](#8-tạo-training-dataset)
9. [Join Với Labels](#9-join-với-labels)
10. [Export Dataset](#10-export-dataset)
11. [Monitoring & Maintenance](#11-monitoring--maintenance)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Tổng Quan

### 1.1. Mục Đích

HDFS được dùng để:
- ✅ Lưu trữ dữ liệu batch từ Spark Streaming (đã gom theo 1 giây)
- ✅ Tổ chức dữ liệu theo partition (year/month/day/hour/minute/second)
- ✅ Tạo training dataset từ dữ liệu lịch sử
- ✅ Join với labels từ `profile.txt`
- ✅ Export dataset cho ML models (Parquet, CSV)

### 1.2. Kiến Trúc

```
┌──────────────────┐
│  Spark Streaming │  Ghi dữ liệu đã xử lý
│  (1 second windows)│
└────────┬─────────┘
         │
         │ Write Parquet files
         ▼
┌──────────────────┐
│  HDFS            │  Distributed storage
│  (NameNode +     │  - Partitioned by time
│   DataNodes)     │  - Parquet format
└────────┬─────────┘
         │
         │ Spark Batch Processing
         ▼
┌──────────────────┐
│  Training Dataset│  - Join với labels
│  (Parquet/CSV)   │  - Feature engineering
└──────────────────┘
```

### 1.3. Luồng Dữ Liệu

1. **Spark Streaming** ghi dữ liệu vào HDFS (mỗi 1 giây)
2. **HDFS** lưu trữ với partitioning theo thời gian
3. **Spark Batch Job** đọc từ HDFS
4. **Join** với labels từ `profile.txt`
5. **Feature Engineering** (aggregate 60 giây thành 1 cycle)
6. **Export** training dataset (Parquet/CSV)

---

## 2. Yêu Cầu Hệ Thống

### 2.1. Phần Mềm

- **Java 8 hoặc 11** (required for Hadoop)
- **Hadoop 3.3.0+** (HDFS)
- **Python 3.8+** (cho PySpark)
- **Apache Spark** (đã setup từ guide trước)

### 2.2. Tài Nguyên

- **RAM:** Tối thiểu 4GB (khuyến nghị 8GB+)
- **CPU:** 2+ cores
- **Disk:** 50GB+ free space (cho data storage)

### 2.3. Dependencies

Cần thêm vào `requirements.txt`:
```
pyspark>=3.3.0
pyarrow>=10.0.0  # Cho Parquet support
```

---

## 3. Cài Đặt HDFS

### 3.1. Download Hadoop

```bash
# Tạo thư mục cho Hadoop
mkdir -p ~/hadoop
cd ~/hadoop

# Download Hadoop 3.3.6 (hoặc version mới nhất)
wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz

# Giải nén
tar -xzf hadoop-3.3.6.tar.gz
cd hadoop-3.3.6

# Set environment variables
export HADOOP_HOME=$(pwd)
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
```

### 3.2. Cấu Hình Java

```bash
# Tìm Java home
export JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:bin/java::")

# Verify
echo $JAVA_HOME
java -version
```

### 3.3. Cấu Hình SSH (cho distributed mode)

```bash
# Generate SSH key (nếu chưa có)
ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa

# Copy key
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

# Test SSH
ssh localhost
```

---

## 4. Cấu Hình HDFS

### 4.1. Cấu Hình Core

Tạo/sửa file `$HADOOP_HOME/etc/hadoop/core-site.xml`:

```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/tmp/hadoop-${user.name}</value>
    </property>
</configuration>
```

### 4.2. Cấu Hình HDFS

Tạo/sửa file `$HADOOP_HOME/etc/hadoop/hdfs-site.xml`:

```xml
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/tmp/hadoop-${user.name}/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/tmp/hadoop-${user.name}/datanode</value>
    </property>
    <property>
        <name>dfs.permissions</name>
        <value>false</value>
    </property>
</configuration>
```

### 4.3. Cấu Hình YARN (Optional, cho Spark)

Tạo/sửa file `$HADOOP_HOME/etc/hadoop/yarn-site.xml`:

```xml
<configuration>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.nodemanager.env-whitelist</name>
        <value>JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME</value>
    </property>
</configuration>
```

### 4.4. Format HDFS

```bash
# Format namenode (chỉ chạy lần đầu!)
$HADOOP_HOME/bin/hdfs namenode -format
```

⚠️ **Warning:** Chỉ format lần đầu. Format lại sẽ mất tất cả dữ liệu!

### 4.5. Start HDFS

```bash
# Start NameNode và DataNode
$HADOOP_HOME/sbin/start-dfs.sh

# Verify
jps
# Should see:
# - NameNode
# - DataNode
# - SecondaryNameNode (optional)
```

### 4.6. Verify HDFS

```bash
# List root directory
hdfs dfs -ls /

# Tạo test directory
hdfs dfs -mkdir -p /test
hdfs dfs -put README.md /test/
hdfs dfs -cat /test/README.md

# Xóa test
hdfs dfs -rm -r /test
```

### 4.7. Web UI

Truy cập HDFS Web UI:
```
http://localhost:9870
```

Xem:
- Cluster overview
- Browse file system
- NameNode information

---

## 5. Cấu Trúc Dữ Liệu

### 5.1. Directory Structure

```
hdfs://localhost:9000/
  /hydraulic_data/
    /streaming/              # Dữ liệu từ Spark Streaming
      /year=2025/
        /month=11/
          /day=08/
            /hour=14/
              /minute=30/
                /second=45/
                  /cycle=0/
                    part-00000.parquet
                    part-00001.parquet
                    ...
    /batch/                  # Dữ liệu batch processing
      /year=2025/
        /month=11/
          /day=08/
            /hour=14/
              /minute=30/
                /cycle=0/
                  aggregated.parquet
    /training/               # Training datasets
      /raw/                  # Raw features
      /processed/            # Processed features
      /labeled/              # With labels
```

### 5.2. Parquet File Schema

Mỗi Parquet file chứa:

```python
{
  "window_start": "2025-11-08T14:30:45",
  "window_end": "2025-11-08T14:30:46",
  "cycle": 0,
  "second_in_cycle": 45,
  
  # 100Hz sensors (100 samples/giây)
  "PS1_values": [151.19, 152.33, ..., 153.45],  # Array[100]
  "PS1_avg": 152.5,
  "PS1_min": 151.19,
  "PS1_max": 153.45,
  "PS1_std": 0.8,
  "PS1_count": 100,
  
  # ... (tương tự cho PS2-6, EPS1)
  
  # 10Hz sensors (10 samples/giây)
  "FS1_values": [12.5, 12.6, ..., 12.9],  # Array[10]
  "FS1_avg": 12.7,
  "FS1_min": 12.5,
  "FS1_max": 12.9,
  "FS1_std": 0.1,
  "FS1_count": 10,
  
  # ... (tương tự cho FS2)
  
  # 1Hz sensors (1 sample/giây)
  "TS1_avg": 45.2,  # Single value
  "TS1_min": 45.2,
  "TS1_max": 45.2,
  "TS1_std": 0.0,
  "TS1_count": 1,
  
  # ... (tương tự cho TS2-4, VS1, CE, CP, SE)
  
  # Calculated features
  "pressure_mean": 152.5,
  "pressure_std": 0.8,
  "temperature_mean": 45.2,
  "flow_mean": 12.7,
  "pressure_rate_of_change": 0.5,
  ...
}
```

---

## 6. Ghi Dữ Liệu Vào HDFS

### 6.1. Từ Spark Streaming

Xem phần 8 trong `SPARK_STREAMING_SETUP.md` để ghi từ Spark Streaming.

### 6.2. Từ Spark Batch Job

Tạo file `src/spark_batch_write.py`:

```python
#!/usr/bin/env python3
"""
Spark Batch Job - Ghi dữ liệu vào HDFS
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from datetime import datetime

def create_spark_session():
    """Tạo SparkSession"""
    spark = SparkSession.builder \
        .appName("HydraulicSystemBatchWrite") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


def write_to_hdfs(df, output_path, partition_cols=None):
    """Ghi DataFrame vào HDFS dạng Parquet"""
    
    writer = df.write \
        .mode("overwrite") \
        .format("parquet") \
        .option("compression", "snappy")
    
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
    
    writer.save(output_path)
    
    print(f"✅ Written to {output_path}")


def main():
    """Main function"""
    spark = create_spark_session()
    
    # Ví dụ: Đọc từ source và ghi vào HDFS
    # (Thay bằng source thực tế của bạn)
    
    # Tạo sample data
    from pyspark.sql.types import *
    
    schema = StructType([
        StructField("window_start", TimestampType(), True),
        StructField("cycle", IntegerType(), True),
        StructField("PS1_avg", DoubleType(), True),
        StructField("PS2_avg", DoubleType(), True),
        # ... thêm các fields khác
    ])
    
    # Sample data
    data = [
        (datetime(2025, 11, 8, 14, 30, 45), 0, 151.19, 178.41),
        (datetime(2025, 11, 8, 14, 30, 46), 0, 152.33, 179.22),
        # ...
    ]
    
    df = spark.createDataFrame(data, schema)
    
    # Thêm partition columns
    df_partitioned = df \
        .withColumn("year", year("window_start")) \
        .withColumn("month", month("window_start")) \
        .withColumn("day", dayofmonth("window_start")) \
        .withColumn("hour", hour("window_start")) \
        .withColumn("minute", minute("window_start")) \
        .withColumn("second", second("window_start"))
    
    # Ghi vào HDFS
    output_path = "hdfs://localhost:9000/hydraulic_data/batch"
    write_to_hdfs(
        df_partitioned,
        output_path,
        partition_cols=["year", "month", "day", "hour", "minute", "second", "cycle"]
    )
    
    spark.stop()


if __name__ == "__main__":
    main()
```

### 6.3. Verify Data

```bash
# List files
hdfs dfs -ls -R /hydraulic_data/batch/

# Check file size
hdfs dfs -du -h /hydraulic_data/batch/

# Read sample (nếu có parquet-tools)
parquet-tools head hdfs://localhost:9000/hydraulic_data/batch/year=2025/month=11/day=08/hour=14/minute=30/second=45/cycle=0/part-00000.parquet
```

---

## 7. Đọc Dữ Liệu Từ HDFS

### 7.1. Đọc với Spark

Tạo file `src/spark_batch_read.py`:

```python
#!/usr/bin/env python3
"""
Spark Batch Job - Đọc dữ liệu từ HDFS
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *

def create_spark_session():
    """Tạo SparkSession"""
    spark = SparkSession.builder \
        .appName("HydraulicSystemBatchRead") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


def read_from_hdfs(spark, hdfs_path, filters=None):
    """Đọc Parquet files từ HDFS"""
    
    df = spark.read.parquet(hdfs_path)
    
    # Apply filters nếu có
    if filters:
        for col_name, value in filters.items():
            df = df.filter(col(col_name) == value)
    
    return df


def main():
    """Main function"""
    spark = create_spark_session()
    
    # Đọc từ HDFS
    hdfs_path = "hdfs://localhost:9000/hydraulic_data/batch"
    
    # Đọc tất cả
    df = read_from_hdfs(spark, hdfs_path)
    
    print(f"✅ Read {df.count()} records")
    print("\nSchema:")
    df.printSchema()
    
    print("\nSample data:")
    df.show(5, truncate=False)
    
    # Đọc với filter (partition pruning)
    df_filtered = read_from_hdfs(
        spark,
        hdfs_path,
        filters={"year": 2025, "month": 11, "day": 8, "cycle": 0}
    )
    
    print(f"\n✅ Filtered: {df_filtered.count()} records")
    
    spark.stop()


if __name__ == "__main__":
    main()
```

### 7.2. Query với Spark SQL

```python
# Register as table
df.createOrReplaceTempView("hydraulic_data")

# Query
result = spark.sql("""
    SELECT 
        cycle,
        AVG(PS1_avg) as avg_pressure,
        MAX(PS1_max) as max_pressure,
        COUNT(*) as record_count
    FROM hydraulic_data
    WHERE year = 2025 AND month = 11 AND day = 8
    GROUP BY cycle
    ORDER BY cycle
""")

result.show()
```

---

## 8. Tạo Training Dataset

### 8.1. Aggregate 60 Giây Thành 1 Cycle

Tạo file `src/create_training_dataset.py`:

```python
#!/usr/bin/env python3
"""
Tạo Training Dataset từ HDFS
- Aggregate 60 giây thành 1 cycle
- Join với labels
- Feature engineering
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd

def create_spark_session():
    """Tạo SparkSession"""
    spark = SparkSession.builder \
        .appName("CreateTrainingDataset") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


def load_labels(spark, labels_path):
    """Load labels từ profile.txt"""
    # Đọc file local (hoặc từ HDFS)
    labels_df = pd.read_csv(labels_path, sep='\t', header=None)
    labels_df.columns = [
        'cycle',
        'cooler_condition',
        'valve_condition',
        'pump_leakage',
        'accumulator_pressure',
        'stable_flag'
    ]
    
    # Convert to Spark DataFrame
    labels_spark = spark.createDataFrame(labels_df)
    
    return labels_spark


def aggregate_by_cycle(df):
    """Aggregate 60 giây thành 1 cycle"""
    
    # Group by cycle và tính toán features
    df_aggregated = df \
        .groupBy("cycle") \
        .agg(
            # Pressure sensors (100Hz)
            avg("PS1_avg").alias("PS1_mean"),
            stddev("PS1_avg").alias("PS1_std"),
            min("PS1_min").alias("PS1_min"),
            max("PS1_max").alias("PS1_max"),
            # ... tương tự cho PS2-6, EPS1
            
            # Flow sensors (10Hz)
            avg("FS1_avg").alias("FS1_mean"),
            stddev("FS1_avg").alias("FS1_std"),
            # ... tương tự cho FS2
            
            # Temperature sensors (1Hz)
            avg("TS1_avg").alias("TS1_mean"),
            stddev("TS1_avg").alias("TS1_std"),
            # ... tương tự cho TS2-4, VS1, CE, CP, SE
            
            # Calculated features
            avg("pressure_mean").alias("pressure_mean"),
            stddev("pressure_mean").alias("pressure_std"),
            avg("temperature_mean").alias("temperature_mean"),
            avg("flow_mean").alias("flow_mean"),
            
            # Count
            count("*").alias("second_count")  # Should be 60
        )
    
    return df_aggregated


def calculate_cycle_features(df):
    """Tính toán features cho mỗi cycle"""
    
    df_features = df \
        .withColumn("pressure_range",
            col("PS1_max") - col("PS1_min")
        ) \
        .withColumn("temperature_range",
            col("TS1_max") - col("TS1_min")
        ) \
        .withColumn("pressure_variability",
            col("PS1_std") / (col("PS1_mean") + 1e-6)
        ) \
        .withColumn("flow_pressure_ratio",
            col("FS1_mean") / (col("pressure_mean") + 1e-6)
        )
    
    return df_features


def join_with_labels(df_features, labels_df):
    """Join với labels"""
    
    df_labeled = df_features \
        .join(labels_df, "cycle", "inner") \
        .orderBy("cycle")
    
    return df_labeled


def main():
    """Main function"""
    spark = create_spark_session()
    
    # 1. Đọc dữ liệu từ HDFS
    print("📊 Reading data from HDFS...")
    hdfs_path = "hdfs://localhost:9000/hydraulic_data/batch"
    df = spark.read.parquet(hdfs_path)
    
    print(f"✅ Read {df.count()} records")
    
    # 2. Aggregate theo cycle
    print("\n🔄 Aggregating by cycle...")
    df_aggregated = aggregate_by_cycle(df)
    
    print(f"✅ Aggregated to {df_aggregated.count()} cycles")
    
    # 3. Tính toán features
    print("\n🧮 Calculating features...")
    df_features = calculate_cycle_features(df_aggregated)
    
    # 4. Load labels
    print("\n📋 Loading labels...")
    labels_path = "data/profile.txt"
    labels_df = load_labels(spark, labels_path)
    
    print(f"✅ Loaded {labels_df.count()} labels")
    
    # 5. Join với labels
    print("\n🔗 Joining with labels...")
    df_labeled = join_with_labels(df_features, labels_df)
    
    print(f"✅ Joined dataset: {df_labeled.count()} cycles")
    
    # 6. Verify
    print("\n📊 Sample data:")
    df_labeled.show(5, truncate=False)
    
    print("\n📈 Statistics:")
    df_labeled.describe().show()
    
    # 7. Ghi training dataset
    print("\n💾 Writing training dataset...")
    output_path = "hdfs://localhost:9000/hydraulic_data/training/labeled"
    
    df_labeled.write \
        .mode("overwrite") \
        .format("parquet") \
        .option("compression", "snappy") \
        .save(output_path)
    
    print(f"✅ Written to {output_path}")
    
    # 8. Export CSV (optional)
    print("\n📄 Exporting CSV...")
    csv_path = "hdfs://localhost:9000/hydraulic_data/training/csv"
    
    df_labeled.write \
        .mode("overwrite") \
        .format("csv") \
        .option("header", "true") \
        .save(csv_path)
    
    print(f"✅ Written CSV to {csv_path}")
    
    spark.stop()


if __name__ == "__main__":
    main()
```

---

## 9. Join Với Labels

### 9.1. Load Labels từ File

```python
def load_labels_from_file(spark, file_path):
    """Load labels từ profile.txt"""
    
    # Đọc file local
    labels_pd = pd.read_csv(
        file_path,
        sep='\t',
        header=None,
        names=[
            'cycle',
            'cooler_condition',
            'valve_condition',
            'pump_leakage',
            'accumulator_pressure',
            'stable_flag'
        ]
    )
    
    # Convert to Spark DataFrame
    labels_df = spark.createDataFrame(labels_pd)
    
    return labels_df
```

### 9.2. Load Labels từ HDFS

```python
def load_labels_from_hdfs(spark, hdfs_path):
    """Load labels từ HDFS"""
    
    labels_df = spark.read \
        .option("sep", "\t") \
        .option("header", "false") \
        .csv(hdfs_path)
    
    # Rename columns
    labels_df = labels_df.select(
        col("_c0").alias("cycle").cast(IntegerType()),
        col("_c1").alias("cooler_condition").cast(IntegerType()),
        col("_c2").alias("valve_condition").cast(IntegerType()),
        col("_c3").alias("pump_leakage").cast(IntegerType()),
        col("_c4").alias("accumulator_pressure").cast(IntegerType()),
        col("_c5").alias("stable_flag").cast(IntegerType())
    )
    
    return labels_df
```

### 9.3. Join

```python
# Inner join (chỉ cycles có labels)
df_labeled = df_features.join(labels_df, "cycle", "inner")

# Left join (giữ tất cả cycles, null cho cycles không có labels)
df_labeled = df_features.join(labels_df, "cycle", "left")

# Verify join
print(f"Features: {df_features.count()}")
print(f"Labels: {labels_df.count()}")
print(f"Joined: {df_labeled.count()}")
```

---

## 10. Export Dataset

### 10.1. Export Parquet

```python
df_labeled.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("hdfs://localhost:9000/hydraulic_data/training/labeled")
```

### 10.2. Export CSV

```python
df_labeled.write \
    .mode("overwrite") \
    .format("csv") \
    .option("header", "true") \
    .option("sep", ",") \
    .save("hdfs://localhost:9000/hydraulic_data/training/csv")
```

### 10.3. Export to Local

```python
# Copy từ HDFS về local
df_labeled.coalesce(1).write \
    .mode("overwrite") \
    .format("csv") \
    .option("header", "true") \
    .save("file:///path/to/local/training_dataset.csv")
```

### 10.4. Download từ HDFS

```bash
# Download Parquet
hdfs dfs -get /hydraulic_data/training/labeled /local/path/

# Download CSV
hdfs dfs -get /hydraulic_data/training/csv /local/path/
```

---

## 11. Monitoring & Maintenance

### 11.1. HDFS Health Check

```bash
# Check HDFS status
hdfs dfsadmin -report

# Check disk usage
hdfs dfs -du -h /hydraulic_data/

# Check file count
hdfs dfs -count /hydraulic_data/
```

### 11.2. Cleanup Old Data

```bash
# Xóa dữ liệu cũ (ví dụ: > 30 ngày)
hdfs dfs -rm -r /hydraulic_data/streaming/year=2025/month=10/

# Hoặc dùng retention policy
```

### 11.3. Backup

```bash
# Backup to another location
hdfs dfs -cp /hydraulic_data/training /backup/hydraulic_data/training
```

---

## 12. Troubleshooting

### 12.1. HDFS Not Starting

**Lỗi:** `NameNode not starting`

**Giải pháp:**
```bash
# Check logs
tail -f $HADOOP_HOME/logs/hadoop-*-namenode-*.log

# Check Java
echo $JAVA_HOME

# Reformat (⚠️ mất dữ liệu!)
$HADOOP_HOME/bin/hdfs namenode -format
```

### 12.2. Permission Denied

**Lỗi:** `Permission denied`

**Giải pháp:**
```bash
# Disable permissions (development only)
# Đã set trong hdfs-site.xml: dfs.permissions = false

# Hoặc set permissions
hdfs dfs -chmod -R 777 /hydraulic_data
```

### 12.3. Out of Space

**Lỗi:** `No space left on device`

**Giải pháp:**
```bash
# Check disk usage
df -h

# Cleanup old data
hdfs dfs -rm -r /hydraulic_data/streaming/year=2024/

# Increase disk space
```

### 12.4. Slow Reads

**Lỗi:** `Slow query performance`

**Giải pháp:**
- Use partition pruning (filter by partition columns)
- Use column pruning (select only needed columns)
- Use compression (snappy)
- Optimize file size (coalesce)

---

## 13. Best Practices

1. **Partitioning:** Partition theo thời gian để query nhanh
2. **Compression:** Dùng Snappy cho Parquet
3. **File Size:** Giữ file size 128MB-256MB
4. **Schema Evolution:** Dùng schema registry nếu có
5. **Monitoring:** Monitor disk usage và health
6. **Backup:** Backup training datasets định kỳ

---

## 14. Next Steps

Sau khi setup HDFS:
1. ✅ Verify data flow từ Spark Streaming
2. ✅ Test đọc/ghi operations
3. ✅ Tạo training dataset
4. ✅ Join với labels
5. ✅ Export cho ML models
6. ✅ Setup monitoring

---

## 📚 References

- [HDFS User Guide](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html)
- [Parquet Format](https://parquet.apache.org/)
- [Spark SQL Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html)


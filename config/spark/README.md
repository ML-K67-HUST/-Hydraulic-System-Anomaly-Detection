# ⚡ Spark Configuration

Thư mục này chứa các cấu hình cho Apache Spark Structured Streaming.

## 📁 Files

- **`spark-defaults.conf`** - Spark configuration

  - Memory settings
  - Streaming settings
  - Kafka integration
  - Adaptive query execution

- **`log4j.properties`** - Logging configuration
  - Log levels
  - Console output format
  - Suppress noisy loggers

## 🚀 Usage

### Quick Start

Xem hướng dẫn chi tiết: **[docs/SPARK_STREAMING.md](../docs/SPARK_STREAMING.md)**

### Local Development

```bash
# Install PySpark
pip install pyspark

# Run locally
./scripts/run_spark_streaming_local.sh
```

### Cluster Mode

```bash
# Start Spark cluster
docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker

# Submit job
./scripts/submit_spark_streaming.sh
```

## 📊 Features

Spark Structured Streaming consumer:

- ✅ **Real-time aggregations** - 1-minute windows
- ✅ **Per-sensor metrics** - Count, avg, max, min, sum
- ✅ **Watermark handling** - Late data support
- ✅ **Fault tolerance** - Checkpoint-based recovery
- ✅ **Scalable** - Distributed processing

## 🔧 Configuration

### Memory Settings

Default in `spark-defaults.conf`:

- Driver: 2GB
- Executor: 2GB

Adjust based on your data volume.

### Window Size

Currently: **1 minute windows**

Modify in `src/spark_streaming_consumer.py`:

```python
.groupBy(window("event_timestamp", "1 minute"), "sensor")
```

### Checkpoint Location

Default: `/tmp/spark-checkpoints/hydraulic-streaming`

Change in `spark-defaults.conf`:

```conf
spark.sql.streaming.checkpointLocation    /your/path
```

## 📈 Output

Spark Streaming outputs:

- **Console** - For monitoring (every 10 seconds)
- **Memory table** - Queryable via Spark SQL (`hydraulic_aggregations`)

## 🔗 Related Files

- **`src/spark_streaming_consumer.py`** - Main application
- **`scripts/submit_spark_streaming.sh`** - Submit to cluster
- **`scripts/run_spark_streaming_local.sh`** - Run locally
- **`docs/SPARK_STREAMING.md`** - Complete guide

## 🐳 Docker Setup

Docker Compose services:

- `spark-master` (port 7077, 8080)
- `spark-worker`

Start with:

```bash
docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker
```

Monitor at: http://localhost:8080

---

**Status:** ✅ Ready to use! See [SPARK_STREAMING.md](../docs/SPARK_STREAMING.md) for details.

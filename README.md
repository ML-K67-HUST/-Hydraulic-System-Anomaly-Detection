### Hydraulic System Anomaly Detection (Kappa Architecture)

This repository provides configuration, infrastructure, and documentation to implement a real-time anomaly detection pipeline for hydraulic cooler condition monitoring using a Kappa-style architecture (stream-first, with batch for reporting/training).

The goal is to detect degradation in the hydraulic cooler condition in near real time, aggregating sensor streams, and alerting when critical thresholds are crossed.

#### Key Components
- **Data Ingestion (Kafka)**: Convert CSV dataset cycles into a continuous, partitioned event stream.
- **Stream Processing (Spark Structured Streaming)**: Windowed aggregations, watermarks, and alerting logic.
- **Serving Layers**:
  - **Data Lake (HDFS/Parquet)**: Full history of raw and aggregated records for analysis.
  - **NoSQL (MongoDB)**: Low-latency sink for active alerts and latest rollups.
- **Batch (Spark Batch)**: Scheduled reports and ML model training with MLlib.

---

### Repository Structure

```text
config/
  kafka/
    topics.yaml            # Topics, partitions, retention
    producer.yaml          # Producer settings: keying, rate, serialization
    schema.json            # Message schema for JSON payloads
  spark/
    streaming.yaml         # Structured Streaming: schema, windows, thresholds, sinks
  batch/
    reports.yaml           # Hourly/Daily reporting job config
    training.yaml          # MLlib training job config
.env.demo               # Environment variables to copy into .env
docker-compose.yml         # Zookeeper, Kafka, HDFS, Spark, MongoDB
requirements.txt           # Python deps for producer and utilities
README.md                  # This file
```

---

### Prerequisites
- Docker and Docker Compose
- Python 3.10+ (for producer utilities and local tooling)
- Sufficient disk/memory for Kafka, HDFS, Spark, and MongoDB containers

Optional for local runs without Docker: Java 8+/11 and Spark 3.5.x

---

### Quick Start

1) Copy environment template and adjust values as needed.

```bash
cp env.demo .env
# PowerShell alternative:
# Copy-Item env.example .env
```

2) Start infrastructure.

```bash
docker compose up -d
```

3) Create Kafka topic (if not auto-created). Example using the compose Kafka broker name `kafka`:

```bash
docker exec -it kafka \
  kafka-topics --bootstrap-server kafka:9092 \
  --create --topic hydraulic_sensor_data --partitions 8 --replication-factor 1 \
  --config cleanup.policy=delete --config retention.ms=604800000
```

4) Prepare data: Place the CSV in a local `data/` directory and update `PRODUCER_CSV_PATH` in `.env` or `config/kafka/producer.yaml`.

5) Run producer (example command once you implement the producer script):

```bash
python producer.py --config config/kafka/producer.yaml
```

6) Run Spark Structured Streaming job (example):

```bash
spark-submit \
  --master spark://spark-master:7077 \
  streaming_job.py --config config/spark/streaming.yaml
```

7) Run batch reports / training (examples):

```bash
spark-submit batch_reports.py --config config/batch/reports.yaml
spark-submit training_job.py --config config/batch/training.yaml
```

---

### Configuration Overview

- `config/kafka/topics.yaml`: Topic definitions (name, partitions, retention).
- `config/kafka/producer.yaml`: CSV path, keying/partitioning strategy, rate control, and serialization.
- `config/kafka/schema.json`: Canonical JSON schema for each sensor event.
- `config/spark/streaming.yaml`: Kafka source, explicit schema reference, watermark/window, aggregations, alert thresholds, and sinks (HDFS/MongoDB).
- `config/batch/reports.yaml`: Hourly/Daily jobs, lookback windows, aggregation targets, and output locations.
- `config/batch/training.yaml`: MLlib training configuration, features/label, split, model hyperparameters, and output paths.

---

### Dataset Notes

Source: `Condition Monitoring of Hydraulic Systems` (UCI). The dataset consists of operational cycles with ~17 sensor/feature columns and a labeled cooler condition column (`cooler_condition`). Map dataset columns to the schema fields in `config/kafka/schema.json`. Key anomaly features include `cooler_efficiency_pct` and temperatures such as `temperature_cooler_out_C`.

---

### Operational Guidance

- **Partitioning**: Messages are keyed by `device_id` (or logical cycle grouping) to ensure ordering per device and parallelism across partitions.
- **Watermarking & Windows**: Default watermark is 10 minutes; window is 5 minutes with 1-minute slide. Adjust for your actual event-time characteristics and latency tolerance.
- **Alerting**: Example rule: 5-min average `cooler_efficiency_pct` < 20% OR 5-min max `temperature_cooler_out_C` > 75°C. Tune thresholds per your environment.
- **Storage**: Raw JSON and windowed aggregates are written to HDFS in Parquet for low-cost analytics and historical modeling.

---



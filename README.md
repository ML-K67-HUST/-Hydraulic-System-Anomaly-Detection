# Hydraulic System Condition Monitoring - Big Data Pipeline

Automated condition monitoring of hydraulic systems using a **Kappa Architecture** (Real-time Stream Processing). This project simulates high-frequency sensor data, processes it via Spark on Kubernetes, and visualizes system health through Grafana.

## 🏗️ Architecture Overview

The pipeline implements a complete dataflow from ingestion to visualization:

1.  **Ingestion**: `Hydraulic Producer` (Python) streams 17 sensor signals and cycle labels to Kafka in an **infinite continuous loop**.
2.  **Streaming & Processing**: 
    *   **Kafka**: Distributed message broker managing sensor topics and analytics updates.
    *   **Spark Streaming**: Performs real-time windowed aggregations (Average, StdDev, Range) to detect signal instability.
3.  **Persistence**: 
    *   **HDFS**: Raw sensor data and labels are stored in partitioned Parquet format for long-term storage and ML training.
    *   **MongoDB**: Stores processed records for historical documentation.
4.  **Monitoring & ML**: 
    *   **MLflow**: Centralized tracking for model training experiments and metrics.
    *   **Anomaly Detection**: Real-time health calculation (0-100%) and threshold alerts.
5.  **Visualization**: Automated Grafana dashboards for system health and Spark analytics.

## 🚀 Quick Start (Automated)

The project includes a comprehensive deployment script that handles cluster creation, custom image building, and HDFS permission initialization.

### 1. Automated Deployment
Run the all-in-one script to set up the Kind cluster and all services:
```bash
./deploy-all.sh
```
*   **Custom Images**: Automatically builds `hadoop-python:3.8` (for executors) and `spark-client:custom` (for the driver) to ensure all dependencies like `numpy` and `mlflow` are pre-installed.
*   **HDFS Init**: Automatically prepares `/user/spark` and `/hydraulic` directories with correct permissions for the Spark user.
*   **Wipes old data**: Automatically clears local PV directories on recreate to prevent stale HDFS data.
*   **Auto Port-Forward**: Automatically starts Grafana port-forwarding on `http://localhost:3000`.

### 2. Accessing the System

| Dashboard | URL | Credentials |
| :--- | :--- | :--- |
| **🎨 Grafana Dashboards** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` |
| **🧪 MLflow UI** | `kubectl port-forward svc/mlflow-server -n monitoring 5000:5000` | N/A |
| **🐘 HDFS Web UI** | `kubectl port-forward -n hdfs svc/hdfs-namenode 9870:9870` | N/A |
| **⚙️ YARN Web UI** | `kubectl port-forward -n hdfs svc/hdfs-resourcemanager 8088:8088` | N/A |

## 📊 Running Spark Jobs

Jobs are submitted via the `spark-submit-client` pod. Scripts are automatically synced to `/tmp/` during deployment.

### 1. Real-time Streaming (The Brain)
Consumes sensor data from Kafka, performs windowed aggregations, and writes results to HDFS (Raw) and Kafka (Analytics).
```bash
kubectl exec -n hdfs spark-submit-client -- bash -c "export POD_IP=\$(hostname -i) && /opt/spark/bin/spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.host=\$POD_IP \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
    /tmp/spark_processor.py"
```

### 2. Machine Learning Trainer (Batch)
Reads historical partitioned Parquet data from HDFS, trains system condition models, and logs results to MLflow.
```bash
kubectl exec -n hdfs spark-submit-client -- bash -c "export POD_IP=\$(hostname -i) && /opt/spark/bin/spark-submit \
    --master yarn \
    --deploy-mode client \
    --conf spark.driver.host=\$POD_IP \
    /tmp/spark_trainer.py"
```

## 🛠️ Advanced Maintenance

### Infinite Data Stream
The producer runs in `--continuous` mode by default, meaning it will randomly pick and stream cycles from the dataset indefinitely. This ensures your dashboard and Spark jobs always have live data.

### Troubleshooting HDFS Permissions
If the Spark job fails with `AccessControlException`, the initialization script might have run too early. Re-run the fix manually:
```bash
kubectl apply -f k8s/hdfs-setup/namenode-setup/hdfs-spark-init.yaml -n hdfs
```

---
**Happy Big Data Processing! 🚀**

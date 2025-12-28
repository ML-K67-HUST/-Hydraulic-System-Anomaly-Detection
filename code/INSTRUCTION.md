# User Guide: Hydraulic System Anomaly Detection Pipeline (End-to-End)

This document provides a step-by-step guide to setting up the infrastructure, running the data pipeline, training the ML model, and monitoring the system.

## 🛠 Prerequisites
Ensure the following tools are installed:
1.  **Docker Desktop** (with Kubernetes enabled or use Kind).
2.  **Kind** (Kubernetes in Docker) - `brew install kind`.
3.  **Kubectl** - `brew install kubectl`.
4.  **Python 3.10+** & **pip**.
5.  **Java 8/11/17** (required for Spark Local execution).

---

## 🚀 Step 1: Infrastructure Setup (UP)

We use automated scripts to provision the cluster and deploy services (Kafka, Zookeeper, HDFS, MongoDB, Prometheus, Grafana, MLflow).

1.  **Start Cluster & Deploy Services**:
    ```bash
    ./start-k8s.sh
    ./deploy-all.sh
    ```
    *Wait 2-5 minutes for all Pods to reach `Running` state.*

2.  **Verify Service Status**:
    ```bash
    kubectl get pods -A
    ```

3.  **Enable Port Forwarding** (Critical!):
    To access service UIs from your local machine (localhost), run this script and **keep the terminal open**:
    ```bash
    ./forward_all.sh
    ```
    *Active Ports:*
    *   Grafana: [http://localhost:3000](http://localhost:3000) (User/Pass: admin/admin)
    *   Spark UI: [http://localhost:4040](http://localhost:4040)
    *   HDFS NameNode: [http://localhost:9870](http://localhost:9870)
    *   YARN UI: [http://localhost:8088](http://localhost:8088)
    *   MLflow UI: [http://localhost:5050](http://localhost:5050)

---

## 🌊 Step 2: Streaming Data Pipeline

The system requires a Producer to simulate sensor data and Spark Streaming to process it.

1.  **Start Data Producer**:
    (Automatically runs in K8s deployment `hydraulic-producer`, but can be restarted to reset data flow)
    ```bash
    kubectl rollout restart deployment hydraulic-producer -n hydraulic
    ```

2.  **Run Spark Streaming Processor**:
    Open a new terminal:
    ```bash
    source venv/bin/activate
    python spark-apps/spark_processor.py
    ```
    *You should see Batches being processed `[Batch ID: ...]`. Clean data is written to `/tmp/hydraulic_data` (local) and HDFS (if connected).*

3.  **Sync Data to HDFS** (Optional/Hybrid Mode):
    To backup local processed data to HDFS (Data Lake):
    ```bash
    ./sync_to_hdfs.sh
    ```

---

## 🧠 Step 3: Machine Learning Pipeline (Training & Registry)

Train a Classification model to detect system faults using the processed data.

1.  **Run Trainer**:
    Open a new terminal (ensure `./forward_all.sh` is running):
    ```bash
    python spark-apps/spark_trainer.py
    ```
    *This script will:*
    *   Load data from HDFS (Fallback to Local if HDFS is unavailable).
    *   Vectorize features (excluding leakage features `CE`, `CP`).
    *   Train Random Forest & Decision Tree models.
    *   Log metrics and register Model Artifacts to **MLflow**.

2.  **Check Results on MLflow**:
    *   URL: [http://localhost:5050](http://localhost:5050)
    *   Experiment: `hydraulic_system_health_fixed`.
    *   Compare Metrics (Accuracy, F1-Score) and Feature Importance.
    *   Check the "Models" tab for registered model versions.

---

## 📊 Step 4: Visualization (Grafana Dashboard)

Monitor real-time sensor data and analytics.

1.  **Configure Datasource (First time only)**:
    ```bash
    python src/setup_grafana_datasource.py
    ```

2.  **Update Dashboard**:
    ```bash
    python src/grafana_spark_dashboard.py
    ```

3.  **View Dashboard**:
    *   URL: [http://localhost:3000](http://localhost:3000)
    *   Open Dashboard: **"Hydraulic System - Prometheus (Raw Data - CLEAN)"**.

---

## 🛑 Step 5: Teardown (DOWN)

To stop all services and clean up resources:

1.  **Stop Local Scripts**:
    *   Press `Ctrl+C` in the terminals running `forward_all.sh`, `spark_processor.py`, and `sync_to_hdfs.sh`.

2.  **Delete Kubernetes Cluster**:
    To completely remove the Kind cluster and all deployments:
    ```bash
    kind delete cluster --name bigdata-cluster
    ```

3.  **Clean Local Data**:
    To remove the temporary data generated during the session:
    ```bash
    rm -rf /tmp/hydraulic_data
    rm -rf mlflow_artifacts
    ```
    *(Note: This deletes all processed parquet files and trained models stored locally.)*

---

## ❓ Troubleshooting

*   **`Connection refused` (MLflow/HDFS/Kafka)**:
    *   Check if `./forward_all.sh` is running. If stopped, restart it.
*   **`NameNode is in SafeMode`**:
    *   Run: `kubectl exec -it -n hdfs <namenode-pod> -- hdfs dfsadmin -safemode leave`.
*   **`No data` on Grafana**:
    *   Verify `spark_processor.py` is running.
    *   Check consumer logs: `kubectl logs -n hydraulic -l app=hydraulic-consumer-prometheus`.

---
*Document created by Antigravity AI Agent.*

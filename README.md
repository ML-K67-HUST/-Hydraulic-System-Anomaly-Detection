# 🔧 Hydraulic System Anomaly Detection (Kubernetes Version)

Production-grade Anomaly Detection Pipeline using **Spark Structured Streaming**, **Kafka**, and **Kubernetes**.

## 🚀 Quick Start (Kubernetes)

### 1. Prerequisites
- **Docker Desktop** (running)
- **Kind** (Kubernetes in Docker) or **Minikube**
- **Kubectl**

### 2. One-Click Deployment
This script builds images, loads them into Kind, and deploys the entire stack (HDFS, Kafka, Spark, Prom/Grafana).

```bash
# Make script executable
chmod +x start-k8s.sh

# Run deployment
./start-k8s.sh
```

### 3. Submit Spark Streaming Job
Once the deployment finishes, you need to manually submit the Spark job from the client pod:

```bash
# Access Spark Client Pod
kubectl exec -it spark-submit-client -n hdfs -- /bin/bash

# Submit Job (Copy & Paste this inside the pod)
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --conf spark.driver.host=$(hostname -i) \
  --conf spark.executor.memory=2g \
  --conf spark.driver.memory=1g \
  --conf spark.executor.cores=2 \
  --conf spark.sql.shuffle.partitions=17 \
  /app/spark-apps/spark_processor.py
```

### 4. Start Data Ingestion (Producer)
Open a new terminal to start simulating sensor data:

```bash
# Install dependencies if needed
pip install kafka-python prometheus-client requests

# Run Producer (Continuous Mode - 100 cycles)
python src/producer.py --continuous 100
```

### 5. Start Analytics Consumer
Open another terminal to process analytics messages:

```bash
python src/consumer_analytics.py
```

### 6. Access Dashboards
- **Grafana**: [http://localhost:3000](http://localhost:3000) (admin/admin)
- **Spark UI**:
  ```bash
  kubectl port-forward pod/spark-submit-client 4040:4040 -n hdfs
  # Open http://localhost:4040
  ```

---

## 🏗️ Architecture

```
Sensors (Python) → Kafka (Hydraulic Topics) → Spark Streaming (ETL/Agg/ML)
                                                  ↓
                                          +-------+-------+
                                          ↓               ↓
                                    HDFS (Parquet)   Kafka (Analytics)
                                          ↓               ↓
                                    Batch Training   Python Consumer
                                                          ↓
                                                     Prometheus/Grafana
```

## 📁 Project Structure

| Directory | Purpose |
|-----------|---------|
| `k8s/` | Kubernetes Manifests (StatefulSets, Services, ConfigMaps) |
| `src/` | Python Code (Producer, Consumer) |
| `spark-apps/` | Spark Logic (Processor, Trainer) |
| `data/` | UCI Raw Dataset |
| `report/` | Project Documentation & Final Report |

## 🔧 Troubleshooting

**1. Spark Job Hanging?**
Check if `spark.driver.host` is set correctly.
```bash
kubectl logs spark-submit-client -n hdfs
```

**2. Kafka Connection Failed?**
Ensure you are using the correct listener:
- Inside K8s: `kafka:29092`
- From Host: `localhost:9092`

**3. Reset Everything**
```bash
kind delete cluster --name bigdata-cluster
kind create cluster --name bigdata-cluster --config cluster-config.yaml
```

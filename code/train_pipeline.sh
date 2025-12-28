#!/bin/bash

# Configuration
SPARK_MASTER_CONTAINER="hydraulic-system-anomaly-detection-spark-master-1"
LABEL_PRODUCER_SCRIPT="src/producer_labels.py"
TRAINER_SCRIPT="/opt/spark-apps/spark_trainer.py"
MLFLOW_UI="http://localhost:5001"

echo "🚀 Starting Measurement & Training Pipeline..."
echo "============================================="

# 1. Ingest Labels (Simulating API Trigger)
echo "📦 Step 1: Ingesting Labels..."
python $LABEL_PRODUCER_SCRIPT
if [ $? -ne 0 ]; then
    echo "❌ Label ingestion failed."
    exit 1
fi
echo "✅ Labels ingested."

# 2. Wait for HDFS
echo "⏳ Step 2: Waiting 10s for HDFS ingestion..."
sleep 10

# 3. Trigger Training Job
echo "🧠 Step 3: Triggering Spark Training Job..."
docker exec -u 0 $SPARK_MASTER_CONTAINER \
  /opt/spark/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mlflow:mlflow-spark:2.3.1 \
  $TRAINER_SCRIPT

if [ $? -eq 0 ]; then
    echo "============================================="
    echo "🎉 Pipeline Completed Successfully!"
    echo "👉 View Model at: $MLFLOW_UI"
else
    echo "❌ Training Job Failed."
    exit 1
fi

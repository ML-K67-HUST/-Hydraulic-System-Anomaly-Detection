#!/bin/bash

# Kill any existing port-forwards to avoid conflicts
pkill -f "kubectl port-forward"
echo "Stopped old port-forwards."

# Start Port Forwards in Background
echo "Starting Port Forwards..."

# 1. Kafka (29092)
kubectl port-forward -n kafka svc/kafka-service 29092:29092 > /dev/null 2>&1 &
echo " - Kafka (29092)"

# 2. HDFS IPC (9000)
kubectl port-forward -n hdfs svc/hdfs-namenode 9000:9000 > /dev/null 2>&1 &
echo " - HDFS IPC (9000)"

# 3. MongoDB (27017)
kubectl port-forward -n default svc/mongodb-service 27017:27017 > /dev/null 2>&1 &
echo " - MongoDB (27017)"

# 4. MLflow (5050 -> 5000)
kubectl port-forward -n default svc/mlflow-server 5050:5000 > /dev/null 2>&1 &
echo " - MLflow (5050)"

# Wait for connections to establish
sleep 5

# Set Environment Variables for Local Run
export KAFKA_BROKER="localhost:29092"
export HDFS_PATH="hdfs://localhost:9000/hydraulic/raw"
export HDFS_LABELS_PATH="hdfs://localhost:9000/hydraulic/labels"

# Explicitly set SPARK_HOME to the pip installed location
# We assume it is in site-packages/pyspark
# If this fails, we will try to find it dynamically, but hardcoding provided path usually works better
export SPARK_HOME="/Users/khangtuan/miniconda3/lib/python3.12/site-packages/pyspark"
export PATH=$SPARK_HOME/bin:$PATH

export PYSPARK_PYTHON=python3
export PYSPARK_DRIVER_PYTHON=python3

echo "==================================================="
echo "🚀 STARTING SPARK JOB (LOCAL MODE)"
echo "   SPARK_HOME: $SPARK_HOME"
echo "   UI: http://localhost:4040"
echo "==================================================="

# Run directly from SPARK_HOME/bin
$SPARK_HOME/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --driver-memory 4g \
  --master "local[*]" \
  spark-apps/spark_processor.py

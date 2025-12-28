#!/bin/bash

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Detecting Pods...${NC}"

# 1. Spark UI (Port 4040)
SPARK_POD=$(kubectl get pods -n hydraulic -l job-name=spark-streaming-job -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$SPARK_POD" ]; then
    echo -e "${GREEN}🚀 Forwarding Spark UI ($SPARK_POD) -> http://localhost:4040${NC}"
    kubectl port-forward -n hydraulic $SPARK_POD 4040:4040 > /dev/null 2>&1 &
    PID_SPARK=$!
else
    echo "⚠️  Spark Driver not found!"
fi

# 2. Grafana (Port 3000)
# Try monitoring namespace first, then all
GRAFANA_POD=$(kubectl get pods -n monitoring -l app=grafana -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$GRAFANA_POD" ]; then
    GRAFANA_POD=$(kubectl get pods -A -l app=grafana -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
fi

if [ -n "$GRAFANA_POD" ]; then
    echo -e "${GREEN}📊 Forwarding Grafana ($GRAFANA_POD) -> http://localhost:3000${NC}"
    kubectl port-forward -n monitoring $GRAFANA_POD 3000:3000 > /dev/null 2>&1 &
    PID_GRAFANA=$!
else
    echo "⚠️  Grafana not found!"
fi

# 3. Hadoop NameNode (Port 9870)
NAMENODE_POD=$(kubectl get pods -n hdfs -l app=hdfs-namenode -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$NAMENODE_POD" ]; then
    echo -e "${GREEN}🐘 Forwarding HDFS NameNode ($NAMENODE_POD) -> http://localhost:9870${NC}"
    kubectl port-forward -n hdfs $NAMENODE_POD 9870:9870 > /dev/null 2>&1 &
    PID_HDFS=$!
fi

# 4. YARN ResourceManager (Port 8088)
RM_POD=$(kubectl get pods -n yarn -l app=yarn-resource-manager -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$RM_POD" ]; then
    echo -e "${GREEN}🧶 Forwarding YARN RM ($RM_POD) -> http://localhost:8088${NC}"
    PID_YARN=$!
fi

# 5. MLflow (Port 5050 -> 5000)
MLFLOW_POD=$(kubectl get pods -n monitoring -l app=mlflow -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$MLFLOW_POD" ]; then
    echo -e "${GREEN}🧪 Forwarding MLflow ($MLFLOW_POD) -> http://localhost:5050${NC}"
    kubectl port-forward -n monitoring $MLFLOW_POD 5050:5000 > /dev/null 2>&1 &
    PID_MLFLOW=$!
fi

echo -e "${GREEN}✅ All forwards active! Press Ctrl+C to stop.${NC}"

# Cleanup on Ctrl+C
trap "kill $PID_SPARK $PID_GRAFANA $PID_HDFS $PID_YARN $PID_MLFLOW 2>/dev/null; echo '🛑 Stopped all forwards.'; exit" INT
wait

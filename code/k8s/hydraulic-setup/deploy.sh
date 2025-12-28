#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   Hydraulic System Deployment Setup      ${NC}"
echo -e "${BLUE}==========================================${NC}"

# 1. Build Docker Image
echo -e "\n${BLUE}[STEP 1] Building Docker Image...${NC}"
# Navigate to hydraulic-app directory relative to this script
# Assuming this script is in k8s/hydraulic-setup/ or k8s/
# Let's assume this script is placed in k8s/hydraulic-setup/deploy.sh
# So hydraulic-app is ../../hydraulic-app
# BUT, best to use absolute path from git root or relative to script location.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
APP_DIR="$PROJECT_ROOT"

if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: hydraulic-app directory not found at $APP_DIR${NC}"
    exit 1
fi

if [[ "$(docker images -q hydraulic-system:latest 2> /dev/null)" == "" ]]; then
    echo "Building from $APP_DIR..."
    docker build -t hydraulic-system:latest -f "$APP_DIR/Dockerfile" "$APP_DIR"
else
    echo "Image hydraulic-system:latest exists, skipping build."
fi

# 2. Load into Kind
echo -e "\n${BLUE}[STEP 2] Loading image into Kind (bigdata-cluster)...${NC}"
kind load docker-image hydraulic-system:latest --name bigdata-cluster

# 3. Apply Manifests
echo -e "\n${BLUE}[STEP 3] Applying Kubernetes Manifests...${NC}"

# We are in k8s/hydraulic-setup/ (via SCRIPT_DIR)
kubectl apply -f "$SCRIPT_DIR/monitoring.yaml"
kubectl apply -f "$SCRIPT_DIR/app.yaml"

# 4. Anomaly Detection Backend
echo -e "\n${BLUE}[STEP 4] Deploying Anomaly Detection...${NC}"
kubectl delete configmap hydraulic-source -n hydraulic 2>/dev/null || true
kubectl create configmap hydraulic-source -n hydraulic --from-file="$APP_DIR/src/consumer_analytics.py"
kubectl apply -f "$SCRIPT_DIR/analytics-consumer.yaml"

# 5. Spark Streaming Analytics (The Unified Logic)
echo -e "\n${BLUE}[STEP 5] Preparing Spark Streaming Analytics...${NC}"
SPARK_CLIENT="spark-submit-client"
NAMESPACE="hdfs"

if kubectl get pod $SPARK_CLIENT -n $NAMESPACE &>/dev/null; then
    echo "Copying $APP_DIR/spark-app/spark_processor.py to $SPARK_CLIENT..."
    kubectl cp "$APP_DIR/spark-app/spark_processor.py" $NAMESPACE/$SPARK_CLIENT:/tmp/spark_processor.py
    kubectl cp "$APP_DIR/spark-app/spark_trainer.py" $NAMESPACE/$SPARK_CLIENT:/tmp/spark_trainer.py
    
    echo -e "\n${GREEN}Hydraulic System Logic is now synced to Spark Client!${NC}"
    echo -e "To start the Spark job, run:"
    echo -e "kubectl exec -it $SPARK_CLIENT -n $NAMESPACE -- bash -c '"
    echo -e "  export KAFKA_BROKER=kafka-service.kafka.svc.cluster.local:9092"
    echo -e "  export HDFS_NAMENODE=hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000"
    echo -e "  export CHECKPOINT_DIR=/user/spark/checkpoints"
    echo -e "  export POD_IP=\$(hostname -i)"
    echo -e "  /opt/spark/bin/spark-submit --master yarn --deploy-mode client \\"
    echo -e "    --conf spark.driver.host=\$POD_IP \\"
    echo -e "    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \\"
    echo -e "    /tmp/spark_processor.py'"
    echo -e "'"
else
    echo "⚠️  Spark client pod not found. Skipping Spark script sync."
fi

# 6. Grafana Dashboard Setup
echo -e "\n${BLUE}[STEP 6] Setting up Grafana Dashboards...${NC}"
echo "Dashboards are automatically initialized by the 'dashboard-init' sidecar in the Grafana pod."
echo "Waiting for Grafana to be ready..."
if kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=120s; then
    echo -e "${GREEN}Grafana is ready and dashboards should be loaded!${NC}"
else
    echo "⚠️  Grafana not ready yet. Dashboards will load once it starts."
fi

echo -e "\n${GREEN}Dashboards should now be available at http://localhost:3000 (after port-forward)${NC}"

echo -e "\n${GREEN}Deployment Completed!${NC}"
echo "Check pods: kubectl get pods -n hydraulic"
echo "Check pods: kubectl get pods -n monitoring"

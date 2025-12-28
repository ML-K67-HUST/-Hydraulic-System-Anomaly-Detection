#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   Hydraulic System K8s Single-Click Deployment    ${NC}"
echo -e "${BLUE}===================================================${NC}"

# 0. Environment Checks
if ! command -v docker &> /dev/null; then echo -e "${RED}Docker not found!${NC}"; exit 1; fi
if ! command -v kubectl &> /dev/null; then echo -e "${RED}Kubectl not found!${NC}"; exit 1; fi

# 1. Build Images
echo -e "\n${BLUE}[STEP 1] Building Docker Images...${NC}"

echo ">> Building hydraulic-system:latest (Root Dockerfile)..."
docker build -t hydraulic-system:latest .

echo ">> Building spark-client:custom..."
docker build -t spark-client:custom -f k8s/hdfs-setup/spark-setup/spark-client-image.Dockerfile k8s/hdfs-setup/spark-setup/

echo ">> Building hadoop-python:3.8 (for HDFS Init)..."
docker build -t hadoop-python:3.8 -f k8s/hdfs-setup/hadoop-python.Dockerfile k8s/hdfs-setup/

# 2. Load Images into Cluster
echo -e "\n${BLUE}[STEP 2] Loading Images into Cluster...${NC}"
CONTEXT=$(kubectl config current-context)
echo "Current Context: $CONTEXT"

if [[ "$CONTEXT" == "kind-"* ]]; then
    CLUSTER_NAME=${CONTEXT#kind-}
    echo "Detected Kind cluster: $CLUSTER_NAME"
    kind load docker-image hydraulic-system:latest --name $CLUSTER_NAME
    kind load docker-image spark-client:custom --name $CLUSTER_NAME
elif [[ "$CONTEXT" == "minikube" ]]; then
    echo "Detected Minikube cluster"
    minikube image load hydraulic-system:latest
    minikube image load spark-client:custom
else
    echo -e "${RED}Warning: Not Kind or Minikube. Image loading might fail if using local images.${NC}"
    echo "Skipping image load step. Ensure your cluster can pull 'hydraulic-system:latest' and 'spark-client:custom'."
fi

# 3. Create Namespaces
echo -e "\n${BLUE}[STEP 3] Creating Namespaces...${NC}"
kubectl create namespace hdfs --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace kafka --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace mongodb --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# 4. Deploy HDFS Stack
echo -e "\n${BLUE}[STEP 4] Deploying HDFS & Spark Stack...${NC}"
kubectl apply -f k8s/hdfs-setup/config.yaml
kubectl apply -f k8s/hdfs-setup/namenode-setup/
kubectl apply -f k8s/hdfs-setup/datanode-setup/node0-setup/
kubectl apply -f k8s/hdfs-setup/yarn-setup/

echo "Waiting for NameNode..."
kubectl rollout status statefulset/hdfs-namenode -n hdfs --timeout=300s

# 5. Deploy Spark Client & Configs
echo -e "\n${BLUE}[STEP 5] Deploying Spark Client...${NC}"
# Creates ConfigMap for Spark Code (so we don't need kubectl cp)
kubectl create configmap spark-app-code -n hdfs --from-file=spark-apps/ --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/hdfs-setup/spark-setup/spark-config.yaml
kubectl apply -f k8s/hdfs-setup/spark-setup/spark-submit.yaml

# 6. Deploy Kafka & Mongo
echo -e "\n${BLUE}[STEP 6] Deploying Infrastructure (Kafka, Mongo)...${NC}"
kubectl apply -f k8s/kafka-setup/
kubectl apply -f k8s/mongodb-setup/

echo "Waiting for Kafka..."
kubectl rollout status statefulset/kafka -n kafka --timeout=300s

# 7. Deploy Hydraulic App
echo -e "\n${BLUE}[STEP 7] Deploying Hydraulic Application...${NC}"
# ConfigMap for consumer scripts
kubectl create namespace hydraulic --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap hydraulic-source -n hydraulic --from-file=src/ --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/hydraulic-setup/app.yaml
kubectl apply -f k8s/hydraulic-setup/analytics-consumer.yaml
kubectl apply -f k8s/hydraulic-setup/monitoring.yaml

echo -e "\n${GREEN}Deployment Complete!${NC}"
echo -e "1. Check HDFS/Spark:  kubectl get pods -n hdfs"
echo -e "2. Check Kafka:       kubectl get pods -n kafka"
echo -e "3. Check App:         kubectl get pods -n hydraulic"
echo -e "\nTo submit the Spark Job:"
echo -e "kubectl exec -it spark-submit-client -n hdfs -- /bin/bash"
echo -e "> /opt/spark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 /app/spark-apps/spark_processor.py"

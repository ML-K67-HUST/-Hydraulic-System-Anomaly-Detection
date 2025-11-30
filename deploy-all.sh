#!/bin/bash

#==============================================================================
# Big Data Cluster Deployment Script (GitHub Synced Version)
# Components: HDFS, YARN, MongoDB, Kafka, Schema Registry, Spark
# Updated: Based on latest GitHub configuration files
#==============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

#==============================================================================
# Configuration
#==============================================================================

CLUSTER_NAME="bigdata-cluster"
BASE_DATA_DIR="/home/phamvanvuhoan/kind-data"

#==============================================================================
# Helper Functions
#==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_step() {
    echo -e "${MAGENTA}[STEP]${NC} $1"
}

wait_for_pods() {
    local namespace=$1
    local label=$2
    local timeout=${3:-300}
    
    print_info "Waiting for pods with label '$label' in namespace '$namespace'..."
    
    local end_time=$((SECONDS + timeout))
    while [ $SECONDS -lt $end_time ]; do
        if kubectl wait --for=condition=ready pod -l "$label" -n "$namespace" --timeout=10s 2>/dev/null; then
            print_success "Pods are ready!"
            return 0
        fi
        echo -n "."
        sleep 5
    done
    
    print_error "Pods failed to become ready within ${timeout}s"
    kubectl get pods -n "$namespace" -l "$label"
    return 1
}

wait_for_job() {
    local namespace=$1
    local job_name=$2
    local timeout=${3:-300}
    
    print_info "Waiting for job '$job_name' to complete..."
    
    if kubectl wait --for=condition=complete job/"$job_name" -n "$namespace" --timeout="${timeout}s" 2>/dev/null; then
        print_success "Job completed successfully!"
        return 0
    else
        print_error "Job failed to complete within ${timeout}s"
        kubectl logs job/"$job_name" -n "$namespace" --tail=100
        return 1
    fi
}

check_pod_status() {
    local namespace=$1
    echo ""
    print_info "Pod status in namespace '$namespace':"
    kubectl get pods -n "$namespace" -o wide
    echo ""
}

#==============================================================================
# Pre-flight Checks
#==============================================================================

print_header "PRE-FLIGHT CHECKS"

# Check required commands
print_step "Checking required tools..."
for cmd in kind kubectl docker; do
    if ! command -v $cmd &> /dev/null; then
        print_error "$cmd is not installed. Please install it first."
        exit 1
    fi
    print_success "$cmd is available"
done

# Check Docker daemon
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker first."
    exit 1
fi
print_success "Docker daemon is running"

# Check and create directories
print_step "Checking/creating data directories..."
REQUIRED_DIRS=(
    "$BASE_DATA_DIR/k8s-master-data"
    "$BASE_DATA_DIR/hdfs-worker-data"
    "$BASE_DATA_DIR/mongodb-data"
    "$BASE_DATA_DIR/kafka-broker-data"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        print_warn "Directory $dir does not exist. Creating..."
        mkdir -p "$dir"
        chmod 777 "$dir"
        print_success "Created $dir"
    else
        print_success "$dir exists"
    fi
done

# Check if configuration files exist
print_step "Checking configuration files..."
REQUIRED_FILES=(
    "cluster-config.yaml"
    "hdfs-setup/config.yaml"
    "hdfs-setup/namenode-setup/sc.yaml"
    "hdfs-setup/datanode-setup/sc.yaml"
    "kafka-setup/sc.yaml"
    "mongodb-setup/sc.yaml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file $file not found!"
        exit 1
    fi
done
print_success "All configuration files present"

#==============================================================================
# Cluster Setup
#==============================================================================

print_header "STEP 1: KUBERNETES CLUSTER SETUP"

if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    print_warn "Cluster '$CLUSTER_NAME' already exists"
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deleting existing cluster..."
        kind delete cluster --name "$CLUSTER_NAME"
        sleep 5
        print_info "Creating new cluster..."
        kind create cluster --config cluster-config.yaml
    else
        print_info "Using existing cluster"
    fi
else
    print_info "Creating Kind cluster..."
    kind create cluster --config cluster-config.yaml
fi

# Wait for cluster to be ready
print_info "Waiting for cluster to be ready..."
sleep 10
kubectl cluster-info --context kind-"$CLUSTER_NAME"
kubectl get nodes
print_success "Cluster is ready"

#==============================================================================
# Node Labeling
#==============================================================================

print_header "STEP 2: NODE LABELING"

print_info "Applying node labels for workload distribution..."

# Get worker node names
WORKERS=($(kubectl get nodes -o name | grep worker | sort))

if [ ${#WORKERS[@]} -lt 4 ]; then
    print_error "Expected 4 worker nodes, found ${#WORKERS[@]}"
    exit 1
fi

# Label nodes
kubectl label ${WORKERS[0]} role=infra-master --overwrite
kubectl label ${WORKERS[1]} role=hdfs-worker --overwrite
kubectl label ${WORKERS[2]} role=mongodb --overwrite
kubectl label ${WORKERS[3]} role=kafka-broker --overwrite

print_success "Node labels applied"
kubectl get nodes -L role

#==============================================================================
# Namespace Creation
#==============================================================================

print_header "STEP 3: NAMESPACE CREATION"

for ns in hdfs kafka mongodb; do
    if kubectl get namespace $ns &>/dev/null; then
        print_info "Namespace '$ns' already exists"
    else
        kubectl create namespace $ns
        print_success "Created namespace '$ns'"
    fi
done

kubectl get namespaces

#==============================================================================
# Storage Classes
#==============================================================================

print_header "STEP 4: STORAGE CLASSES"

print_info "Creating StorageClasses..."
kubectl apply -f hdfs-setup/namenode-setup/sc.yaml
kubectl apply -f hdfs-setup/datanode-setup/sc.yaml
kubectl apply -f kafka-setup/sc.yaml
kubectl apply -f mongodb-setup/sc.yaml

sleep 2
kubectl get storageclass
print_success "StorageClasses created"

#==============================================================================
# Persistent Volumes
#==============================================================================

print_header "STEP 5: PERSISTENT VOLUMES"

print_info "Creating PersistentVolumes..."
kubectl apply -f hdfs-setup/namenode-setup/pv.yaml
kubectl apply -f hdfs-setup/datanode-setup/node0-setup/pv.yaml
kubectl apply -f kafka-setup/pv.yaml
kubectl apply -f mongodb-setup/pv.yaml

sleep 3
kubectl get pv
print_success "PersistentVolumes created"

#==============================================================================
# Persistent Volume Claims
#==============================================================================

print_header "STEP 6: PERSISTENT VOLUME CLAIMS"

print_info "Creating PersistentVolumeClaims..."
kubectl apply -f hdfs-setup/namenode-setup/pvc.yaml
kubectl apply -f hdfs-setup/datanode-setup/node0-setup/pvc.yaml
kubectl apply -f kafka-setup/pvc.yaml
kubectl apply -f mongodb-setup/pvc.yaml

sleep 5

print_info "PVC Status:"
kubectl get pvc --all-namespaces

# Verify PVCs are bound
print_info "Verifying PVC binding..."
for ns in hdfs kafka mongodb; do
    if ! kubectl get pvc -n "$ns" 2>/dev/null | grep -q "Bound"; then
        print_warn "Some PVCs in namespace '$ns' are not bound yet"
    fi
done

#==============================================================================
# ConfigMaps and Secrets
#==============================================================================

print_header "STEP 7: CONFIGMAPS AND SECRETS"

print_info "Creating HDFS ConfigMap..."
kubectl apply -f hdfs-setup/config.yaml -n hdfs

print_info "Creating Spark ConfigMap..."
kubectl apply -f hdfs-setup/spark-setup/spark-config.yaml -n hdfs

print_info "Creating Kafka ConfigMap..."
kubectl apply -f kafka-setup/config.yaml -n kafka

print_info "Creating MongoDB Secret..."
kubectl apply -f mongodb-setup/credential.yaml -n mongodb

sleep 2
print_success "ConfigMaps and Secrets created"

kubectl get configmaps --all-namespaces
kubectl get secrets -n mongodb

#==============================================================================
# HDFS NameNode
#==============================================================================

print_header "STEP 8: HDFS NAMENODE DEPLOYMENT"

print_info "Deploying HDFS NameNode..."
kubectl apply -f hdfs-setup/namenode-setup/deploy.yaml -n hdfs

sleep 15

# Wait for NameNode pod to be created
print_info "Waiting for NameNode pod to be created..."
timeout=60
while [ $timeout -gt 0 ]; do
    if kubectl get pod -n hdfs -l app=hdfs-namenode 2>/dev/null | grep -q "hdfs-namenode"; then
        break
    fi
    sleep 2
    ((timeout-=2))
done

check_pod_status "hdfs"

# Format NameNode
print_info "Formatting HDFS NameNode..."

# Delete old format job if exists
kubectl delete job hdfs-namenode-formatter -n hdfs 2>/dev/null || true

kubectl apply -f hdfs-setup/namenode-setup/format.yaml -n hdfs

if wait_for_job "hdfs" "hdfs-namenode-formatter" 180; then
    print_success "NameNode formatted successfully"
    kubectl delete job hdfs-namenode-formatter -n hdfs
    
    print_info "Restarting NameNode to apply formatting..."
    kubectl rollout restart statefulset hdfs-namenode -n hdfs
    sleep 20
    
    if wait_for_pods "hdfs" "app=hdfs-namenode" 300; then
        print_success "NameNode is ready"
    else
        print_error "NameNode failed to start after formatting"
        check_pod_status "hdfs"
        exit 1
    fi
else
    print_error "Failed to format NameNode"
    check_pod_status "hdfs"
    exit 1
fi

#==============================================================================
# HDFS DataNode
#==============================================================================

print_header "STEP 9: HDFS DATANODE DEPLOYMENT"

print_info "Deploying HDFS DataNode..."
kubectl apply -f hdfs-setup/datanode-setup/node0-setup/deploy.yaml -n hdfs

if wait_for_pods "hdfs" "app=hdfs-datanode" 180; then
    print_success "DataNode is ready"
else
    print_error "DataNode failed to start"
    check_pod_status "hdfs"
fi

# Verify HDFS cluster
print_info "Verifying HDFS cluster..."
sleep 10
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfsadmin -report || true

#==============================================================================
# YARN ResourceManager
#==============================================================================

print_header "STEP 10: YARN RESOURCEMANAGER DEPLOYMENT"

print_info "Deploying YARN ResourceManager..."
kubectl apply -f hdfs-setup/yarn-setup/resource-manager-deploy.yaml -n hdfs

if wait_for_pods "hdfs" "app=hdfs-resourcemanager" 180; then
    print_success "ResourceManager is ready"
else
    print_error "ResourceManager failed to start"
    check_pod_status "hdfs"
fi

#==============================================================================
# YARN NodeManager
#==============================================================================

print_header "STEP 11: YARN NODEMANAGER DEPLOYMENT"

print_info "Deploying YARN NodeManager..."
kubectl apply -f hdfs-setup/yarn-setup/node-manager-deploy.yaml -n hdfs

if wait_for_pods "hdfs" "app=hdfs-nodemanager" 180; then
    print_success "NodeManager is ready"
else
    print_error "NodeManager failed to start"
    check_pod_status "hdfs"
fi

# Verify YARN cluster
print_info "Verifying YARN cluster..."
sleep 10
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list || true

#==============================================================================
# MongoDB
#==============================================================================

print_header "STEP 12: MONGODB DEPLOYMENT"

print_info "Deploying MongoDB..."
kubectl apply -f mongodb-setup/deploy.yaml -n mongodb

if wait_for_pods "mongodb" "app=mongodb" 180; then
    print_success "MongoDB is ready"
    
    # Test MongoDB connection
    print_info "Testing MongoDB connection..."
    sleep 5
    kubectl exec -n mongodb deployment/mongodb -- mongosh --eval "db.version()" -u admin -p password123 --authenticationDatabase admin || print_warn "MongoDB connection test failed (may need more time to initialize)"
else
    print_error "MongoDB failed to start"
    check_pod_status "mongodb"
fi

#==============================================================================
# Kafka
#==============================================================================

print_header "STEP 13: KAFKA DEPLOYMENT"

print_info "Deploying Kafka..."
kubectl apply -f kafka-setup/deploy.yaml -n kafka

sleep 30  # Kafka needs more time to initialize

if wait_for_pods "kafka" "app=kafka" 300; then
    print_success "Kafka is ready"
    
    # Test Kafka
    print_info "Testing Kafka..."
    sleep 10
    kubectl exec -n kafka kafka-0 -- kafka-topics --bootstrap-server localhost:9092 --list || print_warn "Kafka test failed (may need more time)"
else
    print_error "Kafka failed to start"
    check_pod_status "kafka"
fi

#==============================================================================
# Schema Registry
#==============================================================================

print_header "STEP 14: SCHEMA REGISTRY DEPLOYMENT"

print_info "Deploying Schema Registry..."
kubectl apply -f kafka-setup/extension.yaml -n kafka

if wait_for_pods "kafka" "app=schema-registry" 180; then
    print_success "Schema Registry is ready"
else
    print_error "Schema Registry failed to start"
    check_pod_status "kafka"
fi

#==============================================================================
# Final Verification
#==============================================================================

print_header "DEPLOYMENT VERIFICATION"

print_info "Checking all pods status..."
echo ""
echo "=== HDFS Namespace ==="
kubectl get pods -n hdfs -o wide
echo ""
echo "=== Kafka Namespace ==="
kubectl get pods -n kafka -o wide
echo ""
echo "=== MongoDB Namespace ==="
kubectl get pods -n mongodb -o wide
echo ""

print_info "Checking all services..."
echo ""
echo "=== HDFS Services ==="
kubectl get svc -n hdfs
echo ""
echo "=== Kafka Services ==="
kubectl get svc -n kafka
echo ""
echo "=== MongoDB Services ==="
kubectl get svc -n mongodb
echo ""

print_info "Checking PVC status..."
kubectl get pvc --all-namespaces

#==============================================================================
# Summary and Access Information
#==============================================================================

print_header "🎉 DEPLOYMENT COMPLETE! 🎉"

cat <<EOF

${GREEN}All components have been deployed successfully!${NC}

${BLUE}═══════════════════════════════════════════════════════════════${NC}
${BLUE}                    COMPONENT ACCESS URLS                       ${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}1. HDFS NameNode Web UI:${NC}
   ${MAGENTA}kubectl port-forward -n hdfs svc/hdfs-namenode 9870:9870${NC}
   Then open: ${GREEN}http://localhost:9870${NC}

${YELLOW}2. YARN ResourceManager Web UI:${NC}
   ${MAGENTA}kubectl port-forward -n hdfs svc/hdfs-resourcemanager 8088:8088${NC}
   Then open: ${GREEN}http://localhost:8088${NC}

${YELLOW}3. HDFS DataNode Web UI:${NC}
   ${MAGENTA}kubectl port-forward -n hdfs svc/hdfs-datanode 9864:9864${NC}
   Then open: ${GREEN}http://localhost:9864${NC}

${YELLOW}4. YARN NodeManager Web UI:${NC}
   ${MAGENTA}kubectl port-forward -n hdfs daemonset/hdfs-nodemanager 8042:8042${NC}
   Then open: ${GREEN}http://localhost:8042${NC}

${YELLOW}5. MongoDB:${NC}
   ${MAGENTA}kubectl port-forward -n mongodb svc/mongodb-service 27017:27017${NC}
   Connection: ${GREEN}mongodb://admin:password123@localhost:27017${NC}
   
${YELLOW}6. Kafka:${NC}
   ${MAGENTA}kubectl port-forward -n kafka svc/kafka-service 9092:9092${NC}
   Bootstrap servers: ${GREEN}localhost:9092${NC}

${YELLOW}7. Schema Registry:${NC}
   ${MAGENTA}kubectl port-forward -n kafka svc/schema-registry-service 8081:8081${NC}
   URL: ${GREEN}http://localhost:8081${NC}

${BLUE}═══════════════════════════════════════════════════════════════${NC}
${BLUE}                      CREDENTIALS                               ${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}MongoDB:${NC}
  Username: ${GREEN}admin${NC}
  Password: ${GREEN}password123${NC}
  Database: ${GREEN}ecommerce${NC}

${BLUE}═══════════════════════════════════════════════════════════════${NC}
${BLUE}                    QUICK TEST COMMANDS                         ${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}# Check HDFS cluster status${NC}
${MAGENTA}kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfsadmin -report${NC}

${YELLOW}# List HDFS files${NC}
${MAGENTA}kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfs -ls /${NC}

${YELLOW}# Create HDFS directory${NC}
${MAGENTA}kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfs -mkdir -p /data${NC}

${YELLOW}# Check YARN nodes${NC}
${MAGENTA}kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list${NC}

${YELLOW}# List Kafka topics${NC}
${MAGENTA}kubectl exec -n kafka kafka-0 -- kafka-topics --bootstrap-server localhost:9092 --list${NC}

${YELLOW}# Access MongoDB shell${NC}
${MAGENTA}kubectl exec -it -n mongodb deployment/mongodb -- mongosh -u admin -p password123${NC}

${YELLOW}# Check Schema Registry subjects${NC}
${MAGENTA}kubectl port-forward -n kafka svc/schema-registry-service 8081:8081${NC}
${MAGENTA}curl http://localhost:8081/subjects${NC}

${BLUE}═══════════════════════════════════════════════════════════════${NC}
${BLUE}                    NEXT STEPS                                  ${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}1.${NC} Review the ${GREEN}USAGE_GUIDE.md${NC} for detailed operations
${YELLOW}2.${NC} Check ${GREEN}QUICK_REFERENCE.md${NC} for command cheat sheet
${YELLOW}3.${NC} Build and deploy your Spark application using the provided Dockerfile
${YELLOW}4.${NC} Create Kafka topics and start producing data
${YELLOW}5.${NC} Set up your data pipelines

${GREEN}Happy Big Data Processing! 🚀${NC}

${BLUE}═══════════════════════════════════════════════════════════════${NC}

For detailed usage instructions, see: ${GREEN}USAGE_GUIDE.md${NC}
For quick commands, see: ${GREEN}QUICK_REFERENCE.md${NC}

EOF

# Save deployment summary
cat > deployment-summary.txt <<EOF
Deployment completed at: $(date)
Cluster name: $CLUSTER_NAME

Components deployed:
- HDFS NameNode: hdfs-namenode-0
- HDFS DataNode: hdfs-datanode-0
- YARN ResourceManager: hdfs-resourcemanager
- YARN NodeManager: hdfs-nodemanager (DaemonSet)
- MongoDB: mongodb
- Kafka: kafka-0
- Schema Registry: schema-registry

Access the cluster:
kubectl cluster-info --context kind-$CLUSTER_NAME

View all pods:
kubectl get pods --all-namespaces

Delete cluster:
kind delete cluster --name $CLUSTER_NAME
EOF

print_success "Deployment summary saved to: deployment-summary.txt"
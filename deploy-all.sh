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
BASE_DATA_DIR="$HOME/kind-data"  # Dynamic path using $HOME

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

wait_for_hdfs_writable() {
    local timeout=${1:-300}
    print_info "Waiting for HDFS to become writable (SafeMode OFF and Live Nodes > 0)..."
    
    local end_time=$((SECONDS + timeout))
    while [ $SECONDS -lt $end_time ]; do
        # Check Safemode
        if kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfsadmin -safemode get 2>/dev/null | grep -q "Safe mode is OFF"; then
            # Check Live Datanodes
            local live_nodes=$(kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfsadmin -report 2>/dev/null | grep "Live datanodes" | grep -o "[0-9]*")
            if [ -n "$live_nodes" ] && [ "$live_nodes" -gt 0 ]; then
                print_success "HDFS is writable ($live_nodes live datanodes)"
                # Brief settle time
                sleep 5
                return 0
            fi
        fi
        echo -n "."
        sleep 5
    done
    
    print_error "HDFS failed to become writable within ${timeout}s"
    return 1
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

# Check and fix inotify limits (Important for large Kind clusters)
print_step "Checking system inotify limits..."
CURRENT_WATCHES=$(cat /proc/sys/fs/inotify/max_user_watches)
if [ "$CURRENT_WATCHES" -lt 524288 ]; then
    print_warn "inotify max_user_watches ($CURRENT_WATCHES) is too low. Increasing to 524288..."
    sudo sysctl fs.inotify.max_user_watches=524288 >/dev/null
    sudo sysctl fs.inotify.max_user_instances=512 >/dev/null
fi
print_success "inotify limits are sufficient"

# Check Docker daemon
if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker first."
    exit 1
fi
print_success "Docker daemon is running"

# Check and create directories for local PVs
print_step "Checking/creating data directories for local PVs..."
print_info "Base directory: $BASE_DATA_DIR"

REQUIRED_DIRS=(
    "$BASE_DATA_DIR/k8s-master-data"
    "$BASE_DATA_DIR/hdfs-worker-data"
    "$BASE_DATA_DIR/mongodb-data"
    "$BASE_DATA_DIR/kafka-broker-data"
)

CREATED_COUNT=0
EXISTED_COUNT=0

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        print_warn "Directory $dir does not exist. Creating..."
        sudo mkdir -p "$dir"
        sudo chmod 777 "$dir"  # Allow Kind containers to write
        sudo chown $(id -u):$(id -g) "$dir"
        CREATED_COUNT=$((CREATED_COUNT + 1))
        print_success "Created $dir with permissions 777 and owned by $USER"
    else
        # Ensure permissions are correct even if directory exists
        sudo chmod 777 "$dir"
        sudo chown $(id -u):$(id -g) "$dir"
        EXISTED_COUNT=$((EXISTED_COUNT + 1))
        print_success "$dir already exists (permissions updated to 777 and owned by $USER)"
    fi
done

print_info "Summary: Created $CREATED_COUNT directories, $EXISTED_COUNT already existed"
print_success "All required directories are ready for Kind cluster"


# Check if configuration files exist
print_step "Checking configuration files..."
REQUIRED_FILES=(
    #"k8s/cluster-config.yaml"
    "k8s/hdfs-setup/config.yaml"
    "k8s/hdfs-setup/namenode-setup/sc.yaml"
    "k8s/hdfs-setup/datanode-setup/sc.yaml"
    "k8s/kafka-setup/sc.yaml"
    "k8s/mongodb-setup/sc.yaml"
    "k8s/hdfs-setup/spark-setup/spark-submit.yaml"
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

# Generate cluster-config.yaml from template
print_step "Generating cluster configuration..."
if [ ! -f "k8s/cluster-config.yaml.template" ]; then
    print_error "k8s/cluster-config.yaml.template not found!"
    exit 1
fi

# Replace KIND_DATA_DIR with actual BASE_DATA_DIR
sed "s|KIND_DATA_DIR|$BASE_DATA_DIR|g" k8s/cluster-config.yaml.template > cluster-config.yaml
print_success "Generated cluster-config.yaml with paths:"
print_info "  Base directory: $BASE_DATA_DIR"

if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    print_warn "Cluster '$CLUSTER_NAME' already exists"
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deleting existing cluster..."
        kind delete cluster --name "$CLUSTER_NAME"
        
        print_info "Cleaning up old data from host PV directories..."
        for dir in "${REQUIRED_DIRS[@]}"; do
            if [ -d "$dir" ]; then
                print_info "  Wiping $dir..."
                sudo rm -rf "$dir"
            fi
        done
        
        for dir in "${REQUIRED_DIRS[@]}"; do
             sudo mkdir -p "$dir"
             sudo chmod 777 "$dir"
             sudo chown $(id -u):$(id -g) "$dir"
        done

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

#==============================================================================
# Image Preparation (Hadoop + Python 3.8)
#==============================================================================

print_header "STEP 1.5: CUSTOM IMAGE PREPARATION"

print_step "Building Hadoop-Python image..."
docker build -t hadoop-python:3.8 -f k8s/hdfs-setup/hadoop-python.Dockerfile k8s/hdfs-setup/

print_step "Building Spark-Client image..."
docker build -t spark-client:custom -f k8s/hdfs-setup/spark-setup/spark-client-image.Dockerfile k8s/hdfs-setup/spark-setup/

print_step "Loading images into Kind..."
kind load docker-image hadoop-python:3.8 --name "$CLUSTER_NAME"
kind load docker-image spark-client:custom --name "$CLUSTER_NAME"

print_success "Custom images are ready"

kubectl get nodes
print_success "Cluster is ready"

#==============================================================================
# Node Labeling
#==============================================================================

print_header "STEP 2: NODE LABELING"

print_info "Applying node labels for workload distribution..."

# Get worker node names
WORKERS=($(kubectl get nodes -o name | grep worker | sort))

if [ ${#WORKERS[@]} -lt 3 ]; then
    print_error "Expected 3 worker nodes, found ${#WORKERS[@]}"
    exit 1
fi

# Label nodes
kubectl label ${WORKERS[0]} role=infra-master --overwrite
kubectl label ${WORKERS[1]} role=hdfs-worker --overwrite
kubectl label ${WORKERS[2]} role=kafka-broker --overwrite

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
kubectl apply -f k8s/hdfs-setup/namenode-setup/sc.yaml
kubectl apply -f k8s/hdfs-setup/datanode-setup/sc.yaml
kubectl apply -f k8s/kafka-setup/sc.yaml
kubectl apply -f k8s/mongodb-setup/sc.yaml

sleep 2
kubectl get storageclass
print_success "StorageClasses created"

#==============================================================================
# Persistent Volumes
#==============================================================================

print_header "STEP 5: PERSISTENT VOLUMES"

print_info "Creating PersistentVolumes..."
kubectl apply -f k8s/hdfs-setup/namenode-setup/pv.yaml
kubectl apply -f k8s/hdfs-setup/datanode-setup/node0-setup/pv.yaml
kubectl apply -f k8s/kafka-setup/pv.yaml
kubectl apply -f k8s/mongodb-setup/pv.yaml

sleep 3
kubectl get pv
print_success "PersistentVolumes created"

#==============================================================================
# Persistent Volume Claims
#==============================================================================

print_header "STEP 6: PERSISTENT VOLUME CLAIMS"

print_info "Creating PersistentVolumeClaims..."
kubectl apply -f k8s/hdfs-setup/namenode-setup/pvc.yaml
kubectl apply -f k8s/hdfs-setup/datanode-setup/node0-setup/pvc.yaml
kubectl apply -f k8s/kafka-setup/pvc.yaml
kubectl apply -f k8s/mongodb-setup/pvc.yaml

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
kubectl apply -f k8s/hdfs-setup/config.yaml -n hdfs

print_info "Creating Spark ConfigMap..."
kubectl apply -f k8s/hdfs-setup/spark-setup/spark-config.yaml -n hdfs

print_info "Creating Kafka ConfigMap..."
kubectl apply -f k8s/kafka-setup/config.yaml -n kafka

print_info "Creating MongoDB Secret..."
kubectl apply -f k8s/mongodb-setup/credential.yaml -n mongodb

sleep 2
print_success "ConfigMaps and Secrets created"

kubectl get configmaps --all-namespaces
kubectl get secrets -n mongodb

#==============================================================================
# HDFS NameNode
#==============================================================================

print_header "STEP 8: HDFS NAMENODE DEPLOYMENT"

print_info "Deploying HDFS NameNode..."
kubectl apply -f k8s/hdfs-setup/namenode-setup/deploy.yaml -n hdfs

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

kubectl apply -f k8s/hdfs-setup/namenode-setup/format.yaml -n hdfs

if wait_for_job "hdfs" "hdfs-namenode-formatter" 600; then
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
kubectl apply -f k8s/hdfs-setup/datanode-setup/node0-setup/deploy.yaml -n hdfs

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
# HDFS Initialization (Permissions for Spark)
#==============================================================================

print_header "STEP 9.5: HDFS INITIALIZATION"

if wait_for_hdfs_writable 300; then
    print_info "Running HDFS initialization for Spark..."
    kubectl delete job hdfs-spark-init -n hdfs 2>/dev/null || true
    kubectl apply -f k8s/hdfs-setup/namenode-setup/hdfs-spark-init.yaml -n hdfs

    if wait_for_job "hdfs" "hdfs-spark-init" 300; then
        print_success "HDFS initialized successfully"
        kubectl delete job hdfs-spark-init -n hdfs
    else
        print_error "HDFS initialization failed"
        check_pod_status "hdfs"
    fi
else
    print_error "Skipping HDFS initialization as cluster is not writable"
fi

#==============================================================================
# YARN ResourceManager
#==============================================================================

print_header "STEP 10: YARN RESOURCEMANAGER DEPLOYMENT"

print_info "Deploying YARN ResourceManager..."
kubectl apply -f k8s/hdfs-setup/yarn-setup/resource-manager-deploy.yaml -n hdfs

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
kubectl apply -f k8s/hdfs-setup/yarn-setup/node-manager-deploy.yaml -n hdfs

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
# Spark Client
#==============================================================================

print_header "STEP 11.5: SPARK CLIENT DEPLOYMENT"

print_info "Deploying Spark Submit Client..."
kubectl delete pod spark-submit-client -n hdfs --ignore-not-found
kubectl apply -f k8s/hdfs-setup/spark-setup/spark-submit.yaml -n hdfs

if wait_for_pods "hdfs" "app=spark-client" 180; then
    print_success "Spark Client is ready"
else
    print_error "Spark Client failed to start"
    check_pod_status "hdfs"
fi

#==============================================================================
# MongoDB
#==============================================================================

print_header "STEP 12: MONGODB DEPLOYMENT"

print_info "Deploying MongoDB..."
kubectl apply -f k8s/mongodb-setup/deploy.yaml -n mongodb

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
kubectl apply -f k8s/kafka-setup/deploy.yaml -n kafka

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
kubectl apply -f k8s/kafka-setup/extension.yaml -n kafka

if wait_for_pods "kafka" "app=schema-registry" 180; then
    print_success "Schema Registry is ready"
else
    print_error "Schema Registry failed to start"
    check_pod_status "kafka"
fi


#==============================================================================
# Hydraulic System
#==============================================================================

print_header "STEP 15: HYDRAULIC SYSTEM DEPLOYMENT"

print_info "Deploying Hydraulic System..."
if [ -f "k8s/hydraulic-setup/deploy.sh" ]; then
    # chmod +x k8s/hydraulic-setup/deploy.sh
    # ./k8s/hydraulic-setup/deploy.sh
    
    # We inline the call or run the script. 
    # Since deploy.sh assumes relative paths from its own location, let's run it from its dir or fix paths.
    # The deploy.sh I wrote uses absolute paths based on its location. So calling it from here is fine.
    
    bash k8s/hydraulic-setup/deploy.sh
else
    print_warn "k8s/hydraulic-setup/deploy.sh not found. Skipping."
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
echo "=== Hydraulic Services ==="
kubectl get svc -n monitoring
echo ""

print_info "Checking PVC status..."
kubectl get pvc --all-namespaces

#==============================================================================
# Auto Port-Forward
#==============================================================================

print_header "STEP 16: AUTO PORT-FORWARD"

print_info "Starting Grafana port-forward in background..."
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    print_warn "Port 3000 is already in use. Skipping auto port-forward."
else
    # Run in background and redirect output
    nohup kubectl port-forward -n monitoring svc/grafana 3000:3000 > /tmp/grafana_pf.log 2>&1 &
    PF_PID=$!
    print_success "Grafana port-forward started (PID: $PF_PID)"
    print_info "Logs available at: /tmp/grafana_pf.log"
    sleep 2 # Give it a moment to initialize
fi

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
   ${MAGENTA}kubectl port-forward -n hdfs statefulset/hdfs-nodemanager 8042:8042${NC}
   Then open: ${GREEN}http://localhost:8042${NC}

${YELLOW}5. Grafana (Dashboards):${NC}
   ${GREEN}http://localhost:3000${NC} (Auto-forwarded)
   Username: ${GREEN}admin${NC}, Password: ${GREEN}admin${NC}
   
${YELLOW}6. MongoDB:${NC}
   ${MAGENTA}kubectl port-forward -n mongodb svc/mongodb-service 27017:27017${NC}
   Connection: ${GREEN}mongodb://admin:password123@localhost:27017${NC}
   
${YELLOW}7. Kafka:${NC}
   ${MAGENTA}kubectl port-forward -n kafka svc/kafka-service 9092:9092${NC}
   Bootstrap servers: ${GREEN}localhost:9092${NC}

${YELLOW}8. Schema Registry:${NC}
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
- YARN NodeManager: hdfs-nodemanager (StatefulSet)
- MongoDB: mongodb
- Kafka: kafka-0
- Schema Registry: schema-registry
- Hydraulic System: Producer, Consumers, Analytics (Anomaly Detection), Monitoring Stack

Access the cluster:
kubectl cluster-info --context kind-$CLUSTER_NAME

View all pods:
kubectl get pods --all-namespaces

Delete cluster:
kind delete cluster --name $CLUSTER_NAME
EOF

print_success "Deployment summary saved to: deployment-summary.txt"
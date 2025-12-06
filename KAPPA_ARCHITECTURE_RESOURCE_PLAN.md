# Complete Resource Plan - Kappa Architecture on Local Machine

## System Constraints
- **Total RAM**: 14GB physical
- **Currently Used**: 10GB (71%)  
- **Available**: 4GB
- **Swap**: 674MB in use ⚠️

## Architecture: Kappa (Stream Processing)
```
Kafka (ingestion) → Spark Streaming (processing) → MongoDB (serving layer)
                                                   ↓
                                              HDFS (backup/historical)
                                                   ↓
                                            Grafana (monitoring)
```

---

## TIGHT Resource Budget - All Components

### Total Budget Calculation
| Component | CPU Req | Mem Req | CPU Limit | Mem Limit |
|-----------|---------|---------|-----------|-----------|
| **Storage Layer** |
| HDFS NameNode | 500m | 1Gi | 1000m | 2Gi |
| HDFS DataNode (1x) | 300m | 512Mi | 800m | 1Gi |
| MongoDB (1x) | 400m | 800Mi | 1500m | 2Gi |
| **Processing Layer** |
| YARN ResourceManager | 400m | 800Mi | 1000m | 1.5Gi |
| YARN NodeManager (1x) | 800m | 2.5Gi | 3000m | 4Gi |
| **Streaming Layer** |
| Kafka KRaft (1x) | 400m | 800Mi | 1500m | 2Gi |
| Schema Registry | 200m | 256Mi | 500m | 512Mi |
| **Compute Layer** |
| Spark Client | 200m | 384Mi | 500m | 768Mi |
| **Monitoring** |
| Grafana | 100m | 128Mi | 500m | 512Mi |
| **TOTAL REQUESTS** | **3.3 CPU** | **7.2GB** | **9.8 CPU** | **14.3GB** |
| **System Overhead** | ~2 CPU | ~3GB | - | - |
| **GRAND TOTAL** | **~5.3 CPU** | **~10.2GB** | - | - |

**Status**: ✅ Fits in 14GB with ~3.8GB headroom for bursts

---

## Component-by-Component Configuration

### 1. HDFS NameNode
```yaml
# File: hdfs-setup/namenode-setup/deploy.yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

### 2. HDFS DataNode (SINGLE REPLICA)
```yaml
# File: hdfs-setup/datanode-setup/node0-setup/deploy.yaml
spec:
  replicas: 1  # Ensure only 1!
  
resources:
  requests:
    cpu: "300m"
    memory: "512Mi"
  limits:
    cpu: "800m"
    memory: "1Gi"
```

### 3. YARN ResourceManager
```yaml
# File: hdfs-setup/yarn-setup/resource-manager-deploy.yaml
resources:
  requests:
    cpu: "400m"
    memory: "800Mi"
  limits:
    cpu: "1000m"
    memory: "1536Mi"  # 1.5Gi
```

### 4. YARN NodeManager (SINGLE INSTANCE)
```yaml
# File: hdfs-setup/yarn-setup/node-manager-deploy.yaml
# Already updated!
resources:
  requests:
    cpu: "800m"
    memory: "2560Mi"  # 2.5Gi
  limits:
    cpu: "3000m"
    memory: "4Gi"

# YARN Config (already done)
yarn.nodemanager.resource.memory-mb: 3584  # 3.5GB for containers
yarn.nodemanager.resource.cpu-vcores: 2
yarn.scheduler.maximum-allocation-mb: 2048  # 2GB max per container
yarn.scheduler.maximum-allocation-vcores: 2
```

### 5. MongoDB (SINGLE INSTANCE)
```yaml
# File: mongodb-setup/deploy.yaml
spec:
  replicas: 1  # Already set!

resources:
  requests:
    cpu: "400m"
    memory: "800Mi"
  limits:
    cpu: "1500m"
    memory: "2Gi"
```

### 6. Kafka KRaft (SINGLE BROKER)
```yaml
# File: kafka-setup/deploy.yaml
spec:
  replicas: 1  # Already set!

resources:
  requests:
    cpu: "400m"
    memory: "800Mi"
  limits:
    cpu: "1500m"
    memory: "2Gi"

# Add to env in config.yaml
env:
  - name: KAFKA_HEAP_OPTS
    value: "-Xmx512M -Xms512M"  # Reduced heap for local
```

### 7. Schema Registry
```yaml
# File: kafka-setup/extension.yaml (if separate)
resources:
  requests:
    cpu: "200m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

### 8. Spark Submit Client
```yaml
# File: hdfs-setup/spark-setup/spark-submit.yaml
resources:
  requests:
    cpu: "200m"
    memory: "384Mi"
  limits:
    cpu: "500m"
    memory: "768Mi"
```

### 9. Grafana
```yaml
# File: grafana-setup/deploy.yaml (create later)
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

---

## YARN Configuration Updates

Update `hdfs-setup/config.yaml`:

```xml
<!-- Reduce from current 4GB to fit tighter budget -->
<property>
  <name>yarn.nodemanager.resource.memory-mb</name>
  <value>3584</value>
  <description>3.5GB for YARN containers</description>
</property>

<property>
  <name>yarn.nodemanager.resource.cpu-vcores</name>
  <value>2</value>
</property>

<property>
  <name>yarn.scheduler.maximum-allocation-mb</name>
  <value>2048</value>
  <description>Max 2GB per container</description>
</property>

<property>
  <name>yarn.scheduler.maximum-allocation-vcores</name>
  <value>2</value>
</property>

<property>
  <name>yarn.scheduler.capacity.maximum-am-resource-percent</name>
  <value>0.3</value>
  <description>Only 30% for AMs</description>
</property>
```

---

## Spark Configuration Updates

Update `hdfs-setup/spark-setup/spark-config.yaml`:

```properties
# Driver (runs in client pod)
spark.driver.memory=512m
spark.driver.cores=1
spark.driver.maxResultSize=256m

# Executors (run on YARN)
spark.executor.memory=1g
spark.executor.cores=1
spark.executor.instances=2

# Disable dynamic allocation initially
spark.dynamicAllocation.enabled=false

# Streaming settings
spark.streaming.backpressure.enabled=true
spark.streaming.kafka.maxRatePerPartition=1000
```

---

## Deployment Order (Critical!)

### Prerequisites
```bash
# 1. Ensure system has enough free RAM
free -h

# 2. Close unnecessary applications
# 3. Check swap usage
swapon --show
```

### Phase 1: Storage Layer (Deploy First)
```bash
# HDFS
kubectl apply -f hdfs-setup/namenode-setup/
kubectl apply -f hdfs-setup/datanode-setup/node0-setup/

# Wait for healthy
kubectl wait --for=condition=ready pod -l app=hdfs-namenode -n hdfs --timeout=300s

# MongoDB
kubectl apply -f mongodb-setup/
kubectl wait --for=condition=ready pod -l app=mongodb -n mongodb --timeout=300s

# Check RAM usage
free -h
# Should be ~11-12GB used
```

### Phase 2: Processing Layer
```bash
# YARN
kubectl apply -f hdfs-setup/yarn-setup/

# Wait for healthy
kubectl wait --for=condition=ready pod -l app=hdfs-resourcemanager -n hdfs --timeout=300s

# Check RAM usage  
free -h
# Should be ~12-13GB used
```

### Phase 3: Streaming Layer
```bash
# Kafka
kubectl apply -f kafka-setup/

# Wait for healthy
kubectl wait --for=condition=ready pod -l app=kafka -n kafka --timeout=300s

# Check RAM usage
free -h
# Should be ~13-13.5GB used
```

### Phase 4: Compute & Monitoring
```bash
# Spark Client
kubectl apply -f hdfs-setup/spark-setup/spark-submit.yaml

# Grafana (deploy last)
# kubectl apply -f grafana-setup/

# Final check
free -h
kubectl top nodes
kubectl top pods --all-namespaces
```

---

## Testing Strategy

### Test 1: Basic Kafka → Spark → MongoDB Flow
```bash
# 1. Produce to Kafka (small dataset)
kubectl exec -it kafka-0 -n kafka -- \
  kafka-console-producer --bootstrap-server localhost:9092 \
  --topic test-topic

# 2. Run minimal Spark Streaming job
spark-submit --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 1 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  /path/to/streaming-job.py

# 3. Verify in MongoDB
kubectl exec -it mongodb-0 -n mongodb -- mongosh
```

### Test 2: Moderate Load
```bash
# Use 2 executors, 1GB each
spark-submit --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 2 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  /path/to/streaming-job.py
```

---

## Monitoring & Alerts

### Memory Monitoring Script
```bash
#!/bin/bash
# monitor-resources.sh

while true; do
  clear
  echo "=== System Resources ==="
  free -h
  echo ""
  echo "=== Swap Usage ==="
  swapon --show
  echo ""
  echo "=== Top Memory Consumers ==="
  ps aux --sort=-%mem | head -10
  echo ""
  echo "=== Kubernetes Pods ==="
  kubectl top pods --all-namespaces 2>/dev/null || echo "Metrics server not available"
  
  sleep 5
done
```

### Critical Thresholds
- **Swap > 1GB**: Reduce executor count or kill jobs
- **Free RAM < 1GB**: Don't start new jobs
- **OOMKilled pods**: Reduce that component's limits

---

## Emergency Procedures

### Out of Memory
```bash
# 1. Kill Spark jobs
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -list
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -kill <app-id>

# 2. Check what's using memory
kubectl top pods --all-namespaces --sort-by=memory

# 3. Reduce Kafka if needed
kubectl scale statefulset kafka -n kafka --replicas=0
sleep 30
kubectl scale statefulset kafka -n kafka --replicas=1
```

### If System Becomes Unresponsive
```bash
# From another terminal or SSH session
# 1. Kill Kind cluster
kind delete cluster --name bigdata-cluster

# 2. Start fresh with stricter limits
# 3. Or restart your machine
```

---

## Optimization Tips

### 1. Reduce Kafka Log Retention
```yaml
# In kafka-setup/config.yaml
KAFKA_LOG_RETENTION_HOURS: "2"  # Instead of 168
KAFKA_LOG_SEGMENT_BYTES: "536870912"  # 512MB instead of 1GB
```

### 2. Limit MongoDB Oplog
```yaml
# Add to MongoDB startup
--oplogSize 512  # MB
```

### 3. Use Smaller Spark Batch Intervals
```python
# In Spark Streaming code
spark.conf.set("spark.streaming.batchDuration", "5s")  # Shorter batches
```

### 4. Disable Unnecessary Features
```yaml
# Spark
spark.eventLog.enabled=false  # Disable event logging

# Kafka
KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"  # Manual topic creation
```

---

## Success Criteria

✅ **All pods RUNNING**:
```bash
kubectl get pods --all-namespaces | grep -v "Running"
# Should show only Completed or Pending (none)
```

✅ **Memory under 13GB**:
```bash
free -h | grep Mem | awk '{print $3}'
# Should be < 13Gi
```

✅ **Swap under 500MB**:
```bash
free -h | grep Swap | awk '{print $3}'
# Should be < 500Mi
```

✅ **Kappa pipeline works**:
```
Kafka → Spark Streaming → MongoDB (verified data flow)
```

---

## Next Steps

1. ✅ **Apply resource limits** to all components
2. ✅ **Deploy in phases** following the order above
3. ✅ **Monitor RAM** after each phase
4. ✅ **Test data flow** end-to-end
5. ✅ **Add Grafana** only after everything else is stable
6. ✅ **Create monitoring dashboards** in Grafana

**This configuration should allow all components to coexist on your 14GB machine!** 🎯

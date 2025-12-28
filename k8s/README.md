# Big Data Kappa Architecture - Quick Start Guide

**A Kubernetes-based stream processing platform using Kafka, Spark, HDFS, and MongoDB**

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Component Access Guide](#component-access-guide)
   - [Kafka](#1-kafka)
   - [HDFS](#2-hdfs)
   - [MongoDB](#3-mongodb)
   - [Spark](#4-spark)
   - [Schema Registry](#5-schema-registry)
4. [Common Operations](#common-operations)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Troubleshooting](#troubleshooting)
7. [Resource Constraints](#resource-constraints)

---

## 🏗️ Architecture Overview

### Kappa Architecture Pattern
```
┌─────────────┐
│   Kafka     │  ← Data Ingestion (Event Streaming)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Spark     │  ← Stream Processing (Real-time)
│  Streaming  │
└──────┬──────┘
       │
       ├────────→ ┌──────────┐
       │          │ MongoDB  │  ← Serving Layer (Query)
       │          └──────────┘
       │
       └────────→ ┌──────────┐
                  │   HDFS   │  ← Data Lake (Historical)
                  └──────────┘
```

### Components

| Component | Purpose | Namespace | Access Method |
|-----------|---------|-----------|---------------|
| **Kafka** | Event streaming, message broker | `kafka` | kafka-service:9092 |
| **Schema Registry** | Avro schema management | `kafka` | schema-registry-service:8081 |
| **HDFS** | Distributed file storage | `hdfs` | hdfs-namenode-0:9000 |
| **YARN** | Resource management for Spark | `hdfs` | hdfs-resourcemanager:8032 |
| **Spark** | Stream processing | `hdfs` | spark-submit-client pod |
| **MongoDB** | NoSQL serving layer | `mongodb` | mongodb-service:27017 |

---

## ✅ Prerequisites

RUN ./deploy-all.sh

### Check Cluster Status
```bash
# View all components
kubectl get pods --all-namespaces

# Expected output:
# NAMESPACE   NAME                            READY   STATUS
# hdfs        hdfs-namenode-0                 1/1     Running
# hdfs        hdfs-datanode-0                 1/1     Running
# hdfs        hdfs-resourcemanager-xxx        1/1     Running
# hdfs        hdfs-nodemanager-xxx            1/1     Running
# hdfs        spark-submit-client             1/1     Running
# kafka       kafka-0                         1/1     Running
# kafka       schema-registry-xxx             1/1     Running
# mongodb     mongodb-xxx                     1/1     Running
```

### Verify System Resources
```bash
# Check available memory (should have >3GB free)
free -h

# Check Kubernetes nodes
kubectl top nodes

# If metrics-server not installed:
# kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## 🔌 Component Access Guide

## 1. Kafka

### Access Kafka Broker

**From within the cluster:**
```bash
# Enter Kafka pod
kubectl exec -it kafka-0 -n kafka -- bash
```

**From another pod:**
```bash
kafka-service.kafka.svc.cluster.local:9092
```

### Common Kafka Operations

#### List Topics
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics --bootstrap-server localhost:9092 --list
```

#### Create Topic
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic my-topic \
  --partitions 3 \
  --replication-factor 1
```

#### Describe Topic
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics --describe \
  --bootstrap-server localhost:9092 \
  --topic my-topic
```

#### Produce Messages
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic my-topic

# Type messages, press Enter after each
# Press Ctrl+D to exit
```

#### Consume Messages
```bash
# From beginning
kubectl exec -it kafka-0 -n kafka -- \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic my-topic \
  --from-beginning

# Latest messages only
kubectl exec -it kafka-0 -n kafka -- \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic my-topic

# Press Ctrl+C to exit
```

#### Consumer Groups
```bash
# List consumer groups
kubectl exec -it kafka-0 -n kafka -- \
  kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Describe group
kubectl exec -it kafka-0 -n kafka -- \
  kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group my-group --describe
```

#### Delete Topic
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics --delete \
  --bootstrap-server localhost:9092 \
  --topic my-topic
```

---

## 2. HDFS

### Access HDFS

**From within cluster:**
```bash
# Access via NameNode
kubectl exec -it hdfs-namenode-0 -n hdfs -- bash

# Access via Spark client (has HDFS client tools)
kubectl exec -it spark-submit-client -n hdfs -- bash
```

**HDFS URI for applications:**
```
hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000
```

### Common HDFS Operations

#### List Files
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -ls /

# List user directory
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -ls /user/spark
```

#### Create Directory
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -mkdir -p /data/input
```

#### Upload File
```bash
# From local file
echo "Hello HDFS" > test.txt
kubectl cp test.txt hdfs/hdfs-namenode-0:/tmp/test.txt

kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -put /tmp/test.txt /data/input/
```

#### Download File
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -get /data/output/result.txt /tmp/

kubectl cp hdfs/hdfs-namenode-0:/tmp/result.txt ./result.txt
```

#### View File Content
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -cat /data/input/test.txt

# View first 10 lines
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -cat /data/input/test.txt | head -10
```

#### Delete File/Directory
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -rm /data/input/test.txt

# Delete directory recursively
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -rm -r /data/old
```

#### Check Disk Usage
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -df -h

kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -du -h /user/spark
```

#### HDFS Health Check
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfsadmin -report
```

---

## 3. MongoDB

### Access MongoDB

**Via mongosh (MongoDB Shell):**
```bash
# Enter MongoDB pod
kubectl exec -it $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') -n mongodb -- mongosh
```

**Connection string from applications:**
```
mongodb://mongodb-service.mongodb.svc.cluster.local:27017
```

### Common MongoDB Operations

#### Basic Database Operations
```javascript
// In mongosh:

// List databases
show dbs

// Use/create database
use mydb

// List collections
show collections

// Get current database
db.getName()
```

#### Insert Documents
```javascript
// Insert single document
db.events.insertOne({
  id: "evt001",
  timestamp: new Date(),
  value: 100
})

// Insert multiple documents
db.events.insertMany([
  { id: "evt002", timestamp: new Date(), value: 200 },
  { id: "evt003", timestamp: new Date(), value: 300 }
])
```

#### Query Documents
```javascript
// Find all
db.events.find()

// Find with filter
db.events.find({ value: { $gt: 150 } })

// Find one
db.events.findOne({ id: "evt001" })

// Pretty print
db.events.find().pretty()

// Limit results
db.events.find().limit(10)

// Sort
db.events.find().sort({ timestamp: -1 })

// Count
db.events.countDocuments()
db.events.countDocuments({ value: { $gt: 150 } })
```

#### Update Documents
```javascript
// Update one
db.events.updateOne(
  { id: "evt001" },
  { $set: { value: 150, updated: new Date() } }
)

// Update many
db.events.updateMany(
  { value: { $lt: 200 } },
  { $set: { category: "low" } }
)
```

#### Delete Documents
```javascript
// Delete one
db.events.deleteOne({ id: "evt001" })

// Delete many
db.events.deleteMany({ value: { $lt: 100 } })

// Drop collection
db.events.drop()
```

#### Indexes
```javascript
// Create index
db.events.createIndex({ timestamp: 1 })
db.events.createIndex({ id: 1 }, { unique: true })

// List indexes
db.events.getIndexes()

// Drop index
db.events.dropIndex("timestamp_1")
```

#### Exit mongosh
```javascript
exit
```

### External Access (if needed)
```bash
# Port-forward to local machine
kubectl port-forward -n mongodb \
  $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') \
  27017:27017

# Then connect locally:
# mongosh mongodb://localhost:27017
```

---

## 4. Spark

### Access Spark Client

```bash
# Enter Spark submit client pod
kubectl exec -it spark-submit-client -n hdfs -- bash
```

### Submit Spark Jobs

#### Method 1: Interactive (Inside Pod)
```bash
# 1. Enter pod
kubectl exec -it spark-submit-client -n hdfs -- bash

# 2. Set driver IP
export POD_IP=$(hostname -i)

# 3. Submit job
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 1 \
  --conf spark.driver.host=${POD_IP} \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 100
```

#### Method 2: One-Liner (From Outside)
```bash
kubectl exec -n hdfs spark-submit-client -- bash -c '
export POD_IP=$(hostname -i) && 
/opt/spark/bin/spark-submit \
  --master yarn --deploy-mode client \
  --driver-memory 512m --executor-memory 1g \
  --num-executors 1 --conf spark.driver.host=${POD_IP} \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 10
'
```

#### Method 3: Custom Python/Scala Job
```bash
# 1. Copy your script to pod
kubectl cp my_job.py hdfs/spark-submit-client:/tmp/my_job.py

# 2. Submit
kubectl exec -it spark-submit-client -n hdfs -- bash -c '
export POD_IP=$(hostname -i) && 
/opt/spark/bin/spark-submit \
  --master yarn --deploy-mode client \
  --driver-memory 512m --executor-memory 1g \
  --num-executors 2 --conf spark.driver.host=${POD_IP} \
  /tmp/my_job.py
'
```

### Spark Streaming (Kafka → MongoDB)

**Example streaming job** (see `SPARK_JOB_SUBMISSION_GUIDE.md` for full code):
```bash
# Submit streaming job with Kafka & MongoDB connectors
kubectl exec -it spark-submit-client -n hdfs -- bash -c '
export POD_IP=$(hostname -i) && 
/opt/spark/bin/spark-submit \
  --master yarn --deploy-mode client \
  --driver-memory 512m --executor-memory 1g \
  --conf spark.driver.host=${POD_IP} \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  /tmp/streaming_job.py
'
```

### Monitor Spark Jobs

#### List Running Applications
```bash
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -list
```

#### View Application Logs
```bash
# While running
kubectl logs -f spark-submit-client -n hdfs

# YARN logs (after completion)
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn logs -applicationId application_xxx
```

#### Kill Application
```bash
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -kill application_xxx
```

#### Quick Start Script
```bash
# Run test job
./spark-quickstart.sh
```

---

## 5. Schema Registry

### Access Schema Registry

**HTTP API endpoint:**
```
http://schema-registry-service.kafka.svc.cluster.local:8081
```

### Common Operations

#### List Subjects
```bash
kubectl exec -it kafka-0 -n kafka -- \
  curl http://schema-registry-service:8081/subjects
```

#### Register Schema
```bash
kubectl exec -it kafka-0 -n kafka -- bash -c '
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data "{\"schema\": \"{\\\"type\\\": \\\"record\\\", \\\"name\\\": \\\"Event\\\", \\\"fields\\\": [{\\\"name\\\": \\\"id\\\", \\\"type\\\": \\\"string\\\"}, {\\\"name\\\": \\\"value\\\", \\\"type\\\": \\\"int\\\"}]}\"}" \
  http://schema-registry-service:8081/subjects/my-topic-value/versions
'
```

#### Get Latest Schema
```bash
kubectl exec -it kafka-0 -n kafka -- \
  curl http://schema-registry-service:8081/subjects/my-topic-value/versions/latest
```

#### Get Schema by ID
```bash
kubectl exec -it kafka-0 -n kafka -- \
  curl http://schema-registry-service:8081/schemas/ids/1
```

#### Delete Subject
```bash
kubectl exec -it kafka-0 -n kafka -- \
  curl -X DELETE http://schema-registry-service:8081/subjects/my-topic-value
```

---

## 🛠️ Common Operations

### End-to-End Pipeline Test

#### 1. Create Kafka Topic
```bash
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics --create --bootstrap-server localhost:9092 \
  --topic pipeline-test --partitions 1 --replication-factor 1
```

#### 2. Produce Test Data
```bash
kubectl exec -it kafka-0 -n kafka -- bash -c '
echo "{\"id\":\"1\",\"value\":100}" | \
kafka-console-producer --bootstrap-server localhost:9092 --topic pipeline-test
'
```

#### 3. Run Spark Streaming Job
```bash
# Use your streaming job that reads from Kafka and writes to MongoDB
# (See SPARK_JOB_SUBMISSION_GUIDE.md for full example)
```

#### 4. Verify in MongoDB
```bash
kubectl exec -it $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') -n mongodb -- mongosh --eval "
use mydb
db.events.find().pretty()
"
```

#### 5. Backup to HDFS
```bash
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfs -mkdir -p /backup/events
# Use Spark to write results to HDFS
```

---

## 📊 Monitoring & Health Checks

### Check All Components
```bash
# Quick health check script
cat << 'EOF' > health-check.sh
#!/bin/bash
echo "=== Component Health Check ==="
echo ""
echo "HDFS:"
kubectl get pods -n hdfs | grep -E "namenode|datanode|resourcemanager|nodemanager"
echo ""
echo "Kafka:"
kubectl get pods -n kafka
echo ""
echo "MongoDB:"
kubectl get pods -n mongodb
echo ""
echo "=== YARN NodeManagers ==="
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list 2>/dev/null | grep -v WARNING
echo ""
echo "=== HDFS Status ==="
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/hdfs dfsadmin -report 2>/dev/null | head -10
EOF

chmod +x health-check.sh
./health-check.sh
```

### View Logs
```bash
# Kafka
kubectl logs -f kafka-0 -n kafka

# Schema Registry
kubectl logs -f -n kafka -l app=schema-registry

# HDFS NameNode
kubectl logs -f hdfs-namenode-0 -n hdfs

# YARN ResourceManager
kubectl logs -f -n hdfs -l app=hdfs-resourcemanager

# MongoDB
kubectl logs -f -n mongodb -l app=mongodb

# Spark (during job)
kubectl logs -f spark-submit-client -n hdfs
```

### Resource Usage
```bash
# Pod resources
kubectl top pods --all-namespaces

# Node resources
kubectl top nodes

# System memory
free -h

# Swap usage (should be minimal!)
swapon --show
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Pod Not Starting
```bash
# Check pod status
kubectl describe pod <pod-name> -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Check resource constraints
kubectl top nodes
free -h
```

#### 2. Spark Job Stuck in ACCEPTED
```bash
# Check YARN NodeManager
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn node -list

# Check available resources
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn node -list -showDetails

# Check ResourceManager logs
kubectl logs -n hdfs -l app=hdfs-resourcemanager --tail=50
```

#### 3. Kafka Connection Issues
```bash
# Test Kafka connectivity
kubectl exec -it kafka-0 -n kafka -- \
  kafka-broker-api-versions --bootstrap-server localhost:9092

# Check Schema Registry
kubectl exec -it kafka-0 -n kafka -- \
  curl http://schema-registry-service:8081/
```

#### 4. HDFS Issues
```bash
# Check NameNode status
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfsadmin -report

# Check safe mode
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfsadmin -safemode get

# Leave safe mode if needed
kubectl exec -it hdfs-namenode-0 -n hdfs -- \
  /opt/hadoop/bin/hdfs dfsadmin -safemode leave
```

#### 5. MongoDB Connection Issues
```bash
# Test MongoDB connection
kubectl exec -it $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') -n mongodb -- mongosh --eval "db.adminCommand('ping')"

# Check MongoDB logs
kubectl logs -n mongodb -l app=mongodb --tail=50
```

### Emergency Procedures

#### Restart Component
```bash
# Kafka
kubectl delete pod kafka-0 -n kafka

# Schema Registry
kubectl delete pod -n kafka -l app=schema-registry

# HDFS NameNode
kubectl delete pod hdfs-namenode-0 -n hdfs

# YARN NodeManager (will restart on all nodes)
kubectl delete pod -n hdfs -l app=hdfs-nodemanager

# MongoDB
kubectl delete pod -n mongodb -l app=mongodb
```

#### Out of Memory
```bash
# Kill Spark jobs
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -list

kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn application -kill <app-id>

# Check system memory
free -h
swapon --show

# Wait for swap to decrease, then restart components if needed
```

---

## 💾 Resource Constraints

### Local Machine Limits
- **Total RAM**: 14GB
- **Usable for apps**: ~11GB (after K8s overhead)
- **Current allocation**: ~10GB
- **Headroom**: ~3-4GB

### Component Resource Allocation

| Component | CPU Request | Memory Request | Purpose |
|-----------|-------------|----------------|---------|
| NameNode | 500m | 1Gi | HDFS metadata |
| DataNode | 300m | 512Mi | HDFS storage |
| ResourceManager | 400m | 800Mi | YARN coordination |
| NodeManager | 800m | 2.5Gi | Spark executors |
| Kafka | 400m | 800Mi | Event streaming |
| Schema Registry | 200m | 256Mi | Schema management |
| MongoDB | 400m | 800Mi | Serving layer |
| Spark Client | 200m | 384Mi | Job submission |

### Best Practices

1. ⚠️ **Don't run too many Spark executors** - max 2 executors with 1GB each
2. ⚠️ **Monitor swap usage** - if >500MB, reduce workload
3. ⚠️ **Close other applications** when running heavy jobs
4. ⚠️ **One streaming job at a time** initially
5. ✅ **Scale gradually** - test with small data first

---

## 📚 Additional Documentation

- **Spark Job Guide**: `SPARK_JOB_SUBMISSION_GUIDE.md` - Detailed Spark examples
- **Resource Plan**: `KAPPA_ARCHITECTURE_RESOURCE_PLAN.md` - Resource allocation details
- **Quick Start**: `spark-quickstart.sh` - Automated test job

---

## 🆘 Getting Help

### Check Documentation
```bash
# List all markdown docs
ls -la *.md

# Read specific guide
cat SPARK_JOB_SUBMISSION_GUIDE.md
cat KAPPA_ARCHITECTURE_RESOURCE_PLAN.md
```

### Useful kubectl Commands
```bash
# Get all resources in namespace
kubectl get all -n hdfs
kubectl get all -n kafka
kubectl get all -n mongodb

# Describe resource for details
kubectl describe pod <pod-name> -n <namespace>

# Get pod YAML
kubectl get pod <pod-name> -n <namespace> -o yaml

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- <command>

# Port forward (for web UIs)
kubectl port-forward -n hdfs hdfs-namenode-0 9870:9870
# Then access: http://localhost:9870

# Get logs
kubectl logs <pod-name> -n <namespace>
kubectl logs -f <pod-name> -n <namespace>  # follow
kubectl logs <pod-name> -n <namespace> --previous  # previous instance
```

---

## ✅ Quick Reference Card

### Daily Operations
```bash
# Check everything
kubectl get pods --all-namespaces

# Submit Spark job
./spark-quickstart.sh

#Produce to Kafka
kubectl exec -it kafka-0 -n kafka -- kafka-console-producer --bootstrap-server localhost:9092 --topic my-topic

# Query MongoDB
kubectl exec -it $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') -n mongodb -- mongosh

# Check HDFS
kubectl exec -it hdfs-namenode-0 -n hdfs -- /opt/hadoop/bin/hdfs dfs -ls /

# View YARN jobs
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn application -list
```

**Good luck with your big data streaming project! 🚀**

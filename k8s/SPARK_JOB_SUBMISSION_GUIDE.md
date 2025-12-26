# Spark Job Submission Guide - Kappa Architecture

## Prerequisites

### 1. Ensure All Components Are Running
```bash
# Check HDFS
kubectl get pods -n hdfs
# Should see: namenode, datanode, resourcemanager, nodemanager RUNNING

# Check Kafka
kubectl get pods -n kafka
# Should see: kafka-0 RUNNING

# Check MongoDB
kubectl get pods -n mongodb
# Should see: mongodb-xxx RUNNING

# Check Spark client
kubectl get pods -n hdfs | grep spark-submit-client
# Should see: spark-submit-client RUNNING
```

### 2. Verify YARN is Healthy
```bash
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list
# Should show at least 1 NodeManager in RUNNING state
```

---

## Method 1: Submit from Spark Client Pod (Recommended)

### Step 1: Access the Spark Client
```bash
kubectl exec -it spark-submit-client -n hdfs -- bash
```

### Step 2: Set Pod IP for Driver (Important!)
```bash
export POD_IP=$(hostname -i)
echo "Pod IP: $POD_IP"
```

### Step 3: Submit a Simple Test Job
```bash
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

**Expected Output:**
```
...
INFO YarnClientSchedulerBackend: Application application_xxx has started running
...
Pi is roughly 3.141592...
...
INFO SparkContext: Successfully stopped SparkContext
```

---

## Method 2: One-Line kubectl exec (Quick Tests)

```bash
kubectl exec -n hdfs spark-submit-client -- bash -c '
export POD_IP=$(hostname -i) && 
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 1 \
  --conf spark.driver.host=${POD_IP} \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 10
'
```

---

## Example Jobs for Kappa Architecture

### 1. Batch Job: Read from HDFS, Write to MongoDB

**Save this as `batch_job.py` on your local machine:**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("HDFS to MongoDB Batch") \
    .config("spark.mongodb.output.uri", 
            "mongodb://mongodb-service.mongodb.svc.cluster.local:27017/mydb.collection") \
    .getOrCreate()

# Read from HDFS
df = spark.read.text("hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000/data/input.txt")

# Process
df_processed = df.selectExpr("value as message", "current_timestamp() as timestamp")

# Write to MongoDB
df_processed.write \
    .format("mongo") \
    .mode("append") \
    .save()

spark.stop()
```

**Copy to pod and submit:**
```bash
# Copy file to pod
kubectl cp batch_job.py hdfs/spark-submit-client:/tmp/batch_job.py

# Submit
kubectl exec -it spark-submit-client -n hdfs -- bash -c '
export POD_IP=$(hostname -i) &&
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --num-executors 1 \
  --conf spark.driver.host=${POD_IP} \
  --packages org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  /tmp/batch_job.py
'
```

---

### 2. Streaming Job: Kafka → Spark → MongoDB (Kappa!)

**Save as `streaming_job.py`:**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# Define schema for your Kafka messages
schema = StructType([
    StructField("id", StringType(), True),
    StructField("value", IntegerType(), True),
    StructField("timestamp", StringType(), True)
])

spark = SparkSession.builder \
    .appName("Kafka Streaming to MongoDB") \
    .config("spark.mongodb.output.uri", 
            "mongodb://mongodb-service.mongodb.svc.cluster.local:27017/mydb.events") \
    .getOrCreate()

# Read from Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka-service.kafka.svc.cluster.local:9092") \
    .option("subscribe", "events-topic") \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON from Kafka
parsed_df = df.select(
    from_json(col("value").cast("string"), schema).alias("data"),
    col("timestamp").alias("kafka_timestamp")
).select("data.*", "kafka_timestamp")

# Add processing timestamp
processed_df = parsed_df.withColumn("processed_at", current_timestamp())

# Write to MongoDB
query = processed_df \
    .writeStream \
    .format("mongo") \
    .option("checkpointLocation", 
            "hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000/checkpoints/kafka-to-mongo") \
    .outputMode("append") \
    .start()

query.awaitTermination()
```

**Submit streaming job:**
```bash
kubectl cp streaming_job.py hdfs/spark-submit-client:/tmp/streaming_job.py

kubectl exec -it spark-submit-client -n hdfs -- bash -c '
export POD_IP=$(hostname -i) &&
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 2 \
  --conf spark.driver.host=${POD_IP} \
  --conf spark.streaming.backpressure.enabled=true \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
  /tmp/streaming_job.py
'
```

---

### 3. Test the Full Pipeline

**Terminal 1: Produce test data to Kafka**
```bash
kubectl exec -it kafka-0 -n kafka -- bash

# Create topic
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic events-topic \
  --partitions 1 \
  --replication-factor 1

# Produce messages
kafka-console-producer --bootstrap-server localhost:9092 --topic events-topic
# Type messages (JSON format):
{"id":"1","value":100,"timestamp":"2024-12-06T10:00:00"}
{"id":"2","value":200,"timestamp":"2024-12-06T10:01:00"}
{"id":"3","value":300,"timestamp":"2024-12-06T10:02:00"}
# Press Ctrl+D to exit
```

**Terminal 2: Run the streaming job**
```bash
# (Use the streaming_job.py submit command from above)
```

**Terminal 3: Verify in MongoDB**
```bash
kubectl exec -it $(kubectl get pod -n mongodb -l app=mongodb -o jsonpath='{.items[0].metadata.name}') -n mongodb -- mongosh

# In mongosh:
use mydb
db.events.find().pretty()

# Should see your events with processed_at timestamps
```

---

## Common spark-submit Options

### Resource Configuration (For Your 14GB Machine)

**Minimal (for testing):**
```bash
--driver-memory 512m \
--executor-memory 512m \
--executor-cores 1 \
--num-executors 1
```

**Standard (production-like):**
```bash
--driver-memory 512m \
--executor-memory 1g \
--executor-cores 1 \
--num-executors 2
```

**Maximum (use carefully!):**
```bash
--driver-memory 1g \
--executor-memory 1536m \  # 1.5GB
--executor-cores 1 \
--num-executors 2
```

### Important Configurations

```bash
# Driver host (REQUIRED with hostNetwork NodeManager!)
--conf spark.driver.host=${POD_IP}

# Bind to all interfaces
--conf spark.driver.bindAddress=0.0.0.0

# Backpressure for streaming
--conf spark.streaming.backpressure.enabled=true
--conf spark.streaming.kafka.maxRatePerPartition=1000

# Increase timeout if needed
--conf spark.network.timeout=300s

# HDFS block cache
--conf spark.hadoop.fs.hdfs.impl.disable.cache=true
```

---

## Monitoring Jobs

### 1. Check YARN Applications
```bash
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn application -list

# Kill a job if needed
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn application -kill <application_id>
```

### 2. View Application Logs
```bash
# While running
kubectl logs -f spark-submit-client -n hdfs

# YARN logs (after job completes)
kubectl exec -n hdfs hdfs-namenode-0 -- \
  /opt/hadoop/bin/yarn logs -applicationId <application_id>
```

### 3. Check Container Logs on NodeManager
```bash
kubectl exec -n hdfs $(kubectl get pod -n hdfs -l app=hdfs-nodemanager -o jsonpath='{.items[0].metadata.name}') -- \
  ls -la /var/log/hadoop/userlogs/
```

---

## Troubleshooting

### Issue 1: `UnknownHostException` for driver
**Solution:** Always set `--conf spark.driver.host=${POD_IP}`

### Issue 2: Application stays in ACCEPTED state
**Check:**
```bash
# NodeManager health
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list

# Available resources
kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list -showDetails
```

### Issue 3: Out of Memory
**Reduce resources:**
```bash
--driver-memory 256m \
--executor-memory 512m \
--num-executors 1
```

### Issue 4: Container killed by YARN
**Check ResourceManager logs:**
```bash
kubectl logs -n hdfs $(kubectl get pod -n hdfs -l app=hdfs-resourcemanager -o jsonpath='{.items[0].metadata.name}')
```

### Issue 5: `Failed to find data source: kafka`
**Solution:** Add `--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0` to your `spark-submit` command.

### Issue 6: `ModuleNotFoundError: No module named 'numpy'` or `mlflow`
**Status:** ✅ FIXED! The custom Spark client image (`spark-client:custom`) now includes these libraries by default.

If you still encounter this issue on executors, ensure `spark.executorEnv.PYSPARK_PYTHON` is set correctly in `spark-config.yaml` to point to a Python environment where these libraries are installed.

---

## Example: Complete End-to-End Test

```bash
# 1. Create test data in HDFS
kubectl exec -n hdfs spark-submit-client -- bash -c '
echo -e "Line 1\nLine 2\nLine 3" | \
/opt/hadoop/bin/hdfs dfs -put - \
hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000/test/input.txt
'

# 2. Run word count job
kubectl exec -n hdfs spark-submit-client -- bash -c '
export POD_IP=$(hostname -i) &&
/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --num-executors 1 \
  --conf spark.driver.host=${POD_IP} \
  --class org.apache.spark.examples.JavaWordCount \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar \
  hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000/test/input.txt
'

# 3. Verify output
kubectl exec -n hdfs spark-submit-client -- \
  /opt/hadoop/bin/hdfs dfs -ls /user/spark/
```

---

## Performance Tips forLocal Machine

1. **Start small:** Use 1 executor with 512MB-1GB memory
2. **Scale up gradually:** Add executors only if first job succeeds
3. **Monitor memory:** Use `free -h` on your host machine
4. **Watch swap:** If swap increases, reduce executor count
5. **Use checkpointing:** For streaming jobs, checkpoint to HDFS
6. **Batch size:** For streaming, use smaller micro-batch intervals (5-10s)

---

## Next Steps

1. ✅ Test with SparkPi example
2. ✅ Create a simple batch job reading from HDFS
3. ✅ Set up Kafka topic and test streaming
4. ✅ Verify data lands in MongoDB
5. ✅ Add monitoring dashboards in Grafana (Phase 3)

**Your Kappa architecture is ready for Spark jobs!** 🚀

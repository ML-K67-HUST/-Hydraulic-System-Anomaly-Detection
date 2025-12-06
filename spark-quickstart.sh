#!/bin/bash
# Quick Start - Submit your first Spark job

set -e

echo "========================================="
echo "Spark Job Quick Start"
echo "========================================="
echo ""

echo "Step 1: Checking prerequisites..."
echo ""

# Check if spark-submit-client is running
if kubectl get pod spark-submit-client -n hdfs &>/dev/null; then
    echo "✅ Spark client pod is running"
else
    echo "❌ Spark client pod not found!"
    echo "   Run: kubectl apply -f hdfs-setup/spark-setup/spark-submit.yaml"
    exit 1
fi

# Check YARN NodeManager
NM_COUNT=$(kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list 2>/dev/null | grep RUNNING | wc -l)
if [ "$NM_COUNT" -gt 0 ]; then
    echo "✅ YARN has $NM_COUNT NodeManager(s) running"
else
    echo "❌ No YARN NodeManagers running!"
    exit 1
fi

echo ""
echo "Step 2: Submitting test job (SparkPi)..."
echo ""
echo "This will calculate Pi using 100 samples"
echo "Expected duration: 30-60 seconds"
echo ""

# Submit the job
kubectl exec -n hdfs spark-submit-client -- bash -c '
export POD_IP=$(hostname -i)
echo "Driver Host: ${POD_IP}"
echo ""
echo "Submitting job..."
echo ""

/opt/spark/bin/spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 512m \
  --executor-memory 1g \
  --executor-cores 1 \
  --num-executors 1 \
  --conf spark.driver.host=${POD_IP} \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --class org.apache.spark.examples.SparkPi \
  /opt/spark/examples/jars/spark-examples_2.12-3.5.0.jar 100
'

EXIT_CODE=$?

echo ""
echo "========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS! Your first Spark job completed!"
    echo ""
    echo "Next steps:"
    echo "1. Read the full guide: cat SPARK_JOB_SUBMISSION_GUIDE.md"
    echo "2. Try a streaming job: Section 'Streaming Job' in the guide"
    echo "3. Test Kafka → Spark → MongoDB pipeline"
else
    echo "❌ Job failed with exit code: $EXIT_CODE"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check YARN ResourceManager logs:"
    echo "   kubectl logs -n hdfs \$(kubectl get pod -n hdfs -l app=hdfs-resourcemanager -o jsonpath='{.items[0].metadata.name}')"
    echo ""
    echo "2. Check system resources:"
    echo "   free -h"
    echo ""
    echo "3. Check NodeManager status:"
    echo "   kubectl exec -n hdfs hdfs-namenode-0 -- /opt/hadoop/bin/yarn node -list -showDetails"
fi
echo "========================================="

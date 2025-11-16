#!/bin/bash
# Submit Spark Streaming Job (streaming_job.py) to Spark cluster
# Theo kế hoạch triển khai chi tiết

echo "=========================================="
echo "🚀 Submitting Spark Streaming Job"
echo "   (streaming_job.py - Dual Sink: HDFS + MongoDB)"
echo "=========================================="

cd "$(dirname "$0")/.."

# Configuration
SPARK_MASTER="spark://spark-master:7077"
APP_NAME="HydraulicSystemStreaming"
PYTHON_APP="src/streaming_job.py"
CHECKPOINT_DIR="/tmp/spark-checkpoints/streaming_job"

# Check if Spark services are running
echo ""
echo "🔍 Checking Spark services..."
if ! docker ps | grep -q "spark-master"; then
    echo "❌ Spark master not running!"
    echo "   Start with: docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker"
    exit 1
fi

if ! docker ps | grep -q "spark-worker"; then
    echo "❌ Spark worker not running!"
    echo "   Start with: docker-compose -f docker-compose.khang.yml up -d spark-master spark-worker"
    exit 1
fi

echo "✅ Spark services running"

# Check if Kafka is running
echo ""
echo "🔍 Checking Kafka..."
if ! docker ps | grep -q "kafka"; then
    echo "❌ Kafka not running!"
    echo "   Start with: docker-compose -f docker-compose.khang.yml up -d kafka zookeeper"
    exit 1
fi

echo "✅ Kafka running"

# Check if MongoDB is running (optional but recommended)
echo ""
echo "🔍 Checking MongoDB..."
if ! docker ps | grep -q "mongodb"; then
    echo "⚠️  MongoDB not running (optional for hot sink)"
    echo "   Start with: docker-compose -f docker-compose.khang.yml up -d mongodb"
else
    echo "✅ MongoDB running"
fi

# Check if Python app exists
if [ ! -f "$PYTHON_APP" ]; then
    echo "❌ Python app not found: $PYTHON_APP"
    exit 1
fi

# Check if config exists
if [ ! -f "config/spark/streaming.yaml" ]; then
    echo "❌ Config file not found: config/spark/streaming.yaml"
    exit 1
fi

echo ""
echo "📤 Submitting job to Spark cluster..."
echo "   Master: $SPARK_MASTER"
echo "   App: $PYTHON_APP"
echo "   Config: config/spark/streaming.yaml"
echo ""

# Copy files to spark-apps directory for Docker
mkdir -p spark-apps
cp "$PYTHON_APP" spark-apps/
cp -r config spark-apps/ 2>/dev/null || true

# Submit job using spark-submit in Docker
# Packages needed:
# - spark-sql-kafka-0-10: Kafka integration
# - mongo-spark-connector: MongoDB integration
docker exec -it hydraulic-system-anomaly-detection-spark-master-1 \
    /opt/spark/bin/spark-submit \
    --master $SPARK_MASTER \
    --name $APP_NAME \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:10.0.0 \
    --conf spark.sql.streaming.checkpointLocation=$CHECKPOINT_DIR \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.driver.memory=2g \
    --conf spark.executor.memory=2g \
    --py-files /opt/spark-apps/config \
    /opt/spark-apps/streaming_job.py

echo ""
echo "=========================================="
echo "✅ Job submitted!"
echo "=========================================="
echo ""
echo "📊 Monitor at: http://localhost:8080"
echo "🛑 To stop: Press Ctrl+C or kill the job"
echo ""


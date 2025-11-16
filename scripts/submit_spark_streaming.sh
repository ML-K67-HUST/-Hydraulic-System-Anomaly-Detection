#!/bin/bash
# Submit Spark Structured Streaming job to Spark cluster

echo "=========================================="
echo "🚀 Submitting Spark Streaming Job"
echo "=========================================="

cd "$(dirname "$0")/.."

# Configuration
SPARK_MASTER="spark://spark-master:7077"
APP_NAME="HydraulicSystemStreaming"
PYTHON_APP="src/spark_streaming_consumer.py"
CHECKPOINT_DIR="/tmp/spark-checkpoints/hydraulic-streaming"

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

# Check if Python app exists
if [ ! -f "$PYTHON_APP" ]; then
    echo "❌ Python app not found: $PYTHON_APP"
    exit 1
fi

# Submit job using spark-submit in Docker
echo ""
echo "📤 Submitting job to Spark cluster..."
echo "   Master: $SPARK_MASTER"
echo "   App: $PYTHON_APP"
echo ""

docker exec -it hydraulic-system-anomaly-detection-spark-master-1 \
    /opt/spark/bin/spark-submit \
    --master $SPARK_MASTER \
    --name $APP_NAME \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
    --conf spark.sql.streaming.checkpointLocation=$CHECKPOINT_DIR \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.driver.memory=2g \
    --conf spark.executor.memory=2g \
    --py-files /opt/spark-apps/dependencies.zip \
    /opt/spark-apps/spark_streaming_consumer.py

echo ""
echo "=========================================="
echo "✅ Job submitted!"
echo "=========================================="
echo ""
echo "📊 Monitor at: http://localhost:8080"
echo "🛑 To stop: Press Ctrl+C or kill the job"
echo ""


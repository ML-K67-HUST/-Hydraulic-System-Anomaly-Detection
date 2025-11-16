#!/bin/bash
# Run Spark Streaming locally (without Docker cluster)
# Useful for development and testing

echo "=========================================="
echo "🚀 Running Spark Streaming Locally"
echo "=========================================="

cd "$(dirname "$0")/.."

# Configuration
PYTHON_APP="src/spark_streaming_consumer.py"
KAFKA_BROKER="localhost:29092"

# Check if Kafka is running
echo ""
echo "🔍 Checking Kafka..."
if ! docker ps | grep -q "kafka"; then
    echo "❌ Kafka not running!"
    echo "   Start with: docker-compose -f docker-compose.khang.yml up -d kafka zookeeper"
    exit 1
fi

echo "✅ Kafka running at $KAFKA_BROKER"

# Check Python environment
echo ""
echo "🔍 Checking Python environment..."
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Create with: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# Check PySpark
if ! python -c "import pyspark" 2>/dev/null; then
    echo "❌ PySpark not installed!"
    echo "   Install with: pip install pyspark"
    exit 1
fi

echo "✅ Python environment ready"

# Set environment variables
export PYSPARK_PYTHON=$(which python)
export PYSPARK_DRIVER_PYTHON=$(which python)
export SPARK_LOCAL_IP=127.0.0.1

# Run Spark Streaming
echo ""
echo "📤 Starting Spark Streaming..."
echo "   Kafka: $KAFKA_BROKER"
echo "   App: $PYTHON_APP"
echo ""
echo "💡 Tips:"
echo "   - Check Spark UI at http://localhost:4040"
echo "   - Press Ctrl+C to stop"
echo ""

python $PYTHON_APP

echo ""
echo "=========================================="
echo "✅ Streaming stopped"
echo "=========================================="


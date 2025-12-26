#!/bin/bash
# Test consumer connectivity

echo "=========================================="
echo "🧪 Testing Consumer Connection"
echo "=========================================="

cd "$(dirname "$0")/.."
source venv/bin/activate

echo ""
echo "📊 Checking services..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "kafka|prometheus|pushgateway"

echo ""
echo "🔄 Starting consumer (foreground mode)..."
echo "   Press Ctrl+C to stop"
echo ""

cd src
python consumer.py prometheus


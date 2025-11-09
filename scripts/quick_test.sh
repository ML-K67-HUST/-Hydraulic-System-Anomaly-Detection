#!/bin/bash
# Quick test - 1 cycle (60 seconds)

echo "=========================================="
echo "⚡ Quick Test - 1 Cycle (60 seconds)"
echo "=========================================="

cd "$(dirname "$0")/.."
source venv/bin/activate

# Check if consumer is running
if ! pgrep -f "consumer.py prometheus" > /dev/null; then
    echo "🚀 Starting consumer..."
    cd src
    nohup python consumer.py prometheus > ../consumer_prom.log 2>&1 &
    cd ..
    sleep 3
fi

echo ""
echo "📊 Open Grafana now:"
echo "   http://localhost:3000/d/a2744f7e-e88d-4112-aa97-c102abba3fdb/hydraulic-system-prometheus"
echo ""
echo "🔄 Producing 1 cycle of data (60 seconds)..."
echo ""

cd src
python producer.py 0

echo ""
echo "✅ Test complete!"
echo "   Check Grafana dashboard for updates"
echo ""
echo "📈 Stats: ~43,680 messages produced"
echo "=========================================="

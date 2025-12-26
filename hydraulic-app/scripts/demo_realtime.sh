#!/bin/bash
# Demo Real-time Streaming Pipeline
# Chạy producer liên tục để xem data update trên Grafana

echo "=========================================="
echo "🎬 Demo Real-time Hydraulic Monitoring"
echo "=========================================="

cd "$(dirname "$0")/.."

# Check services
echo ""
echo "🔍 Checking services..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep hydraulic

# Activate venv
source venv/bin/activate

echo ""
echo "=========================================="
echo "📊 Grafana Dashboard:"
echo "   http://localhost:3000/d/a2744f7e-e88d-4112-aa97-c102abba3fdb/hydraulic-system-prometheus"
echo "   Login: admin/admin"
echo ""
echo "📈 Prometheus:"
echo "   http://localhost:9090"
echo "=========================================="

# Check if consumer is running
if pgrep -f "consumer.py prometheus" > /dev/null; then
    echo ""
    echo "✅ Consumer is running"
else
    echo ""
    echo "🚀 Starting consumer..."
    cd src
    nohup python consumer.py prometheus > ../consumer_prom.log 2>&1 &
    cd ..
    sleep 3
    echo "✅ Consumer started!"
fi

echo ""
echo "🔄 Starting continuous producer (10 cycles)..."
echo "   Each cycle = 60 seconds"
echo "   Total demo time: ~10 minutes"
echo ""
echo "💡 Tips:"
echo "   - Open Grafana dashboard now"
echo "   - Watch charts update in real-time"
echo "   - Press Ctrl+C to stop anytime"
echo ""
echo "=========================================="
echo ""

# Run producer for 10 cycles
for i in {1..10}; do
    echo "📤 Cycle $i/10 - Producing data..."
    cd src
    python producer.py 0
    cd ..
    
    echo "✅ Cycle $i completed!"
    echo "   📊 Check Grafana for updates"
    echo ""
    
    # Short pause between cycles
    if [ $i -lt 10 ]; then
        echo "⏸️  Pausing 5 seconds before next cycle..."
        sleep 5
        echo ""
    fi
done

echo ""
echo "=========================================="
echo "🎉 Demo completed! 10 cycles finished."
echo ""
echo "📊 Final stats in Grafana:"
echo "   Total messages: ~437,000+ (43,680 per cycle × 10)"
echo ""
echo "🔍 Consumer is still running in background"
echo "   To stop: pkill -f 'consumer.py prometheus'"
echo "=========================================="

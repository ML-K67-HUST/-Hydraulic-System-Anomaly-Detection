#!/bin/bash
# Setup and run Prometheus-based monitoring

echo "=========================================="
echo "🚀 Hydraulic System - Prometheus Setup"
echo "=========================================="

cd "$(dirname "$0")/.."

# Step 1: Install Python dependencies
echo ""
echo "📦 Step 1: Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Step 2: Stop old containers
echo ""
echo "🛑 Step 2: Stopping old containers..."
docker-compose -f docker-compose.khang.yml down
echo "✅ Old containers stopped"

# Step 3: Start new stack (Prometheus + Pushgateway + Grafana)
echo ""
echo "🐳 Step 3: Starting Prometheus stack..."
docker-compose -f docker-compose.khang.yml up -d prometheus pushgateway grafana
sleep 5
echo "✅ Prometheus stack started"

# Step 4: Check services
echo ""
echo "🔍 Step 4: Checking services..."
echo "   Prometheus: http://localhost:9090"
curl -s http://localhost:9090/-/healthy > /dev/null && echo "   ✅ Prometheus healthy" || echo "   ❌ Prometheus not ready"
echo "   Pushgateway: http://localhost:9091"
curl -s http://localhost:9091/ > /dev/null && echo "   ✅ Pushgateway healthy" || echo "   ❌ Pushgateway not ready"
echo "   Grafana: http://localhost:3000"
curl -s http://localhost:3000/api/health > /dev/null && echo "   ✅ Grafana healthy" || echo "   ❌ Grafana not ready"

# Step 5: Wait for Grafana
echo ""
echo "⏳ Step 5: Waiting for Grafana to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "✅ Grafana ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Step 6: Create dashboard
echo ""
echo "📊 Step 6: Creating Grafana dashboard..."
sleep 2
cd src
python grafana_prometheus_dashboard.py
cd ..

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "🌐 Access Points:"
echo "   Grafana:     http://localhost:3000 (admin/admin)"
echo "   Prometheus:  http://localhost:9090"
echo "   Pushgateway: http://localhost:9091"
echo ""
echo "📝 Next Steps:"
echo "   1. Start Kafka/Zookeeper: docker-compose -f docker-compose.khang.yml up -d zookeeper kafka"
echo "   2. Run quick test: ./scripts/quick_test.sh"
echo ""
echo "=========================================="

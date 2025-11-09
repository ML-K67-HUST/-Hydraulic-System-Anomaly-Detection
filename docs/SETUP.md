# 🔧 Setup Guide

Hướng dẫn setup chi tiết từng bước.

---

## 📋 Prerequisites

### 1. Install Docker

```bash
# macOS
brew install docker docker-compose

# Hoặc tải Docker Desktop: https://www.docker.com/products/docker-desktop
```

### 2. Install Python 3.8+

```bash
python3 --version  # Check version
```

---

## 🚀 Setup Process

### Step 1: Clone & Setup Virtual Environment

```bash
cd /path/to/project
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.prometheus.txt
```

**Packages installed:**
- `kafka-python-ng`: Kafka client
- `prometheus-client`: Prometheus metrics

### Step 3: Start Docker Services

```bash
bash scripts/setup_prometheus.sh
```

**Script này sẽ:**
1. ✅ Stop các containers cũ
2. ✅ Start Prometheus stack (Prometheus + Pushgateway + Grafana)
3. ✅ Wait for services ready
4. ✅ Auto-create Grafana dashboard

**Services started:**
- Prometheus (port 9090)
- Pushgateway (port 9091)
- Grafana (port 3000)

### Step 4: Start Kafka & Zookeeper

```bash
docker-compose -f docker-compose.khang.yml up -d zookeeper kafka
```

**Wait 10-15 seconds** for Kafka to be ready.

### Step 5: Verify Services

```bash
# Check Docker containers
docker ps

# Should see:
# - zookeeper
# - kafka
# - prometheus
# - pushgateway
# - grafana
```

**Test URLs:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Pushgateway: http://localhost:9091

---

## 🎬 Running the System

### Option 1: Quick Test (Recommended for first time)

```bash
./scripts/quick_test.sh
```

**This will:**
1. Start consumer in background
2. Run producer for 1 cycle (60 seconds)
3. ~43,680 messages sent

**Expected result:**
- Consumer logs messages
- Prometheus collects metrics
- Grafana dashboard updates

### Option 2: Manual Step-by-Step

```bash
# Terminal 1: Start consumer
cd src
python consumer.py prometheus

# Terminal 2: Start producer (in another terminal)
cd src
python producer.py 0
```

### Option 3: Continuous Demo

```bash
./scripts/demo_realtime.sh
```

**This will:**
- Run 10 cycles (10 minutes total)
- ~437,000 messages
- Perfect for watching real-time updates

---

## 📊 Accessing Grafana

### 1. Open Grafana

http://localhost:3000

**Login:**
- Username: `admin`
- Password: `admin`

### 2. Find Dashboard

Dashboard đã được tự động tạo:

**Dashboards → Hydraulic System - Prometheus**

URL trực tiếp:
```
http://localhost:3000/d/a2744f7e-e88d-4112-aa97-c102abba3fdb/hydraulic-system-prometheus
```

### 3. Dashboard Panels

1. **Total Messages** - Counter tổng messages
2. **Message Rate** - Messages/second
3. **PS1 Pressure** - Time series chart
4. **EPS1 Motor Power** - Time series chart
5. **All Pressure Sensors** - 6 sensors cùng lúc
6. **Temperature Sensors** - 4 temp sensors
7. **Flow Sensors** - 2 flow sensors
8. **Sample Counts** - Bar chart

---

## 🔧 Configuration

### Kafka Topics

Topics được auto-create khi producer chạy:
- `hydraulic-PS1` đến `hydraulic-PS6`
- `hydraulic-EPS1`
- `hydraulic-FS1`, `hydraulic-FS2`
- `hydraulic-TS1` đến `hydraulic-TS4`
- `hydraulic-CE`, `hydraulic-CP`, `hydraulic-SE`, `hydraulic-VS1`

### Prometheus Configuration

File: `prometheus.yml`

```yaml
scrape_interval: 5s  # Scrape mỗi 5 giây
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
```

### Consumer Configuration

File: `src/consumer_prometheus.py`

```python
KAFKA_BROKER = "localhost:29092"
PUSHGATEWAY_URL = "localhost:9091"
CONSUMER_GROUP = "hydraulic-prometheus-group"
```

**Push interval:** Mỗi 2 giây

---

## 🐛 Troubleshooting

### Issue 1: Port already in use

```bash
# Check what's using the port
lsof -i :3000  # Grafana
lsof -i :9090  # Prometheus
lsof -i :9091  # Pushgateway

# Kill process if needed
kill -9 <PID>
```

### Issue 2: Kafka connection error

```bash
# Check Kafka logs
docker logs hydraulic-system-anomaly-detection-kafka-1

# Restart Kafka
docker-compose -f docker-compose.khang.yml restart kafka
```

### Issue 3: Consumer không consume

```bash
# Check consumer groups
docker exec hydraulic-system-anomaly-detection-kafka-1 \
  kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check lag
docker exec hydraulic-system-anomaly-detection-kafka-1 \
  kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group hydraulic-prometheus-group --describe
```

### Issue 4: Grafana dashboard trống

```bash
# Verify Prometheus có data
curl 'http://localhost:9090/api/v1/query?query=hydraulic_messages_total'

# Check consumer logs
cat consumer_prom.log | tail -50

# Restart consumer
pkill -f consumer_prometheus
cd src && python consumer.py prometheus &
```

### Issue 5: Docker out of memory

```bash
# Increase Docker memory in Docker Desktop
# Settings → Resources → Memory: 4GB recommended

# Clean up old containers/volumes
docker system prune -a --volumes
```

---

## 🔄 Cleanup

### Stop All Services

```bash
docker-compose -f docker-compose.khang.yml down
```

### Remove Volumes (⚠️ Data will be lost)

```bash
docker-compose -f docker-compose.khang.yml down -v
```

### Kill Consumer Process

```bash
pkill -f consumer_prometheus
```

---

## 📈 Performance Tips

### 1. Increase Docker Resources

- **Memory:** 4GB+
- **CPUs:** 2+
- **Disk:** 10GB+

### 2. Optimize Kafka

In `docker-compose.khang.yml`:

```yaml
environment:
  KAFKA_HEAP_OPTS: "-Xmx1G -Xms1G"  # Increase if needed
```

### 3. Reduce Grafana Refresh Rate

Default: 5 seconds  
Slower: 10 seconds (less resource usage)

---

## 🎓 Next Steps

1. ✅ Setup hoàn tất → Xem [README.md](../README.md) để chạy demo
2. 📖 Hiểu kiến trúc → Đọc [ARCHITECTURE.md](ARCHITECTURE.md)
3. 🔧 Customize dashboard → Edit panels trong Grafana
4. 📊 Query data → Học PromQL tại http://localhost:9090

---

## 💡 Tips

- **First time:** Chạy `./scripts/quick_test.sh` trước
- **Watch logs:** `tail -f consumer_prom.log` trong khi chạy
- **Monitor Prometheus:** http://localhost:9090/targets
- **Check Pushgateway:** http://localhost:9091/metrics

---

Happy monitoring! 🚀



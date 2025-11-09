# 🔧 Hydraulic System Anomaly Detection

Real-time monitoring system cho hydraulic test rig sử dụng Kafka, Prometheus, và Grafana.

## 📊 Quick Start

### 1. Setup môi trường

```bash
# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start services
bash scripts/setup_prometheus.sh
```

### 2. Chạy real-time streaming

```bash
# Terminal 1: Start consumer
cd src
python consumer.py prometheus &

# Terminal 2: Start producer
# Single cycle
python producer.py 0

# Multiple cycles (10 cycles)
python producer.py 0 10

# Continuous mode (random cycles)
python producer.py --continuous 10

# All 2,205 cycles (~37 hours!)
python producer.py --all
```

### 3. Xem dashboard

Mở Grafana: **http://localhost:3000** (admin/admin)

Dashboard sẽ tự động có sẵn: **Hydraulic System - Prometheus**

---

## 🏗️ Kiến trúc

```
Sensors (17) → Producer → Kafka → Consumer → Pushgateway → Prometheus → Grafana
```

### **17 Sensors:**
- **PS1-6:** Pressure sensors (100Hz)
- **EPS1:** Motor power (100Hz)  
- **FS1-2:** Volume flow (10Hz)
- **TS1-4:** Temperature (1Hz)
- **CE, CP, SE, VS1:** Cooling/vibration (1Hz)

---

## 📁 Cấu trúc project

```
├── src/                          # Source code
│   ├── producer.py               # Kafka producer (17 sensors)
│   ├── consumer.py               # Consumers (Prometheus & MongoDB)
│   └── grafana_prometheus_dashboard.py  # Tạo dashboard
├── scripts/                      # Shell scripts
│   ├── setup_prometheus.sh       # Setup toàn bộ stack
│   ├── quick_test.sh            # Test nhanh 1 cycle
│   └── demo_realtime.sh         # Demo liên tục
├── config/                      # Configurations
│   ├── kafka/                   # Kafka configs
│   ├── spark/                   # Spark configs (optional)
│   └── batch/                   # Batch processing configs
├── data/                        # Sensor data files
│   ├── PS1.txt ... PS6.txt     # Pressure data
│   ├── EPS1.txt                # Motor power
│   ├── FS1.txt, FS2.txt        # Flow rate
│   └── TS1.txt ... TS4.txt     # Temperature
├── grafana/                    # Grafana provisioning
│   └── provisioning/
│       └── datasources/
│           └── prometheus.yml  # Auto-configure Prometheus
├── docker-compose.khang.yml    # Docker services
├── prometheus.yml              # Prometheus config
└── docs/                       # Documentation
    ├── SETUP.md               # Setup chi tiết
    └── ARCHITECTURE.md        # Kiến trúc hệ thống
```

---

## 🚀 Demo Scripts

### **Quick Test (1 cycle - 60s):**
```bash
./scripts/quick_test.sh
```

### **Continuous Demo (10 cycles - 10 phút):**
```bash
./scripts/demo_realtime.sh
```

---

## 🔧 Services & Ports

| Service | Port | URL |
|---------|------|-----|
| Grafana | 3000 | http://localhost:3000 |
| Prometheus | 9090 | http://localhost:9090 |
| Pushgateway | 9091 | http://localhost:9091 |
| Kafka | 9092, 29092 | localhost:29092 |
| Zookeeper | 2181 | localhost:2181 |

---

## 📖 Documentation

- **[SETUP.md](docs/SETUP.md)** - Hướng dẫn setup chi tiết
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Kiến trúc và design decisions
- **[PRODUCER_USAGE.md](docs/PRODUCER_USAGE.md)** - Chi tiết cách dùng producer (single/range/all cycles)

---

## 🎯 Features

✅ **Real-time streaming** với Kafka  
✅ **Time-series storage** với Prometheus  
✅ **Beautiful dashboards** với Grafana  
✅ **17 sensors** với sampling rates chính xác  
✅ **Auto-refresh** dashboard mỗi 5 giây  
✅ **No Enterprise license** - hoàn toàn FREE!  

---

## 🐛 Troubleshooting

### Dashboard không hiển thị data?

```bash
# Check consumer đang chạy
ps aux | grep consumer.py

# Restart consumer nếu cần
pkill -f 'consumer.py prometheus'
cd src && python consumer.py prometheus &

# Verify Prometheus có data
curl 'http://localhost:9090/api/v1/query?query=hydraulic_messages_total'
```

### Services không start được?

```bash
# Stop tất cả
docker-compose -f docker-compose.khang.yml down

# Start lại
bash scripts/setup_prometheus.sh
```

---

## 📝 Requirements

- Python 3.8+
- Docker & Docker Compose
- ~2GB RAM free

---

## 📄 License

MIT License - Dự án học tập Big Data

---

## 👥 Authors

Hydraulic System Anomaly Detection Team

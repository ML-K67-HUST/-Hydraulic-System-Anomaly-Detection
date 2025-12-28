# Producer Usage Guide

## Available Data

Dataset contains **2,205 cycles** of hydraulic system data.

## Usage Options

### 1. Single Cycle
Run một cycle cụ thể:
```bash
python producer.py <cycle_index>
```

**Examples:**
```bash
python producer.py 0      # Chạy cycle đầu tiên
python producer.py 100    # Chạy cycle 100
python producer.py 2204   # Chạy cycle cuối cùng
```

**Time:** ~60 seconds per cycle

---

### 2. Range of Cycles
Chạy một dải cycles liên tiếp:
```bash
python producer.py <start> <end>
```

**Examples:**
```bash
python producer.py 0 10       # Chạy cycles 0-9 (10 cycles)
python producer.py 100 200    # Chạy cycles 100-199 (100 cycles)
python producer.py 0 100      # Chạy 100 cycles đầu tiên
```

**Time:** ~60 seconds × number of cycles + 2 seconds pause between cycles

---

### 3. All Cycles
Chạy TẤT CẢ 2,205 cycles:
```bash
python producer.py --all
```

**Warning:** Rất lâu!
- **Time:** ~2,205 minutes = **36.75 hours** (1.5 ngày)
- **Data:** ~96.5 million messages
- **Disk:** ~10+ GB

**Recommended:** Chỉ dùng cho batch processing hoặc testing hệ thống

---

### 4. Continuous Mode
Chạy n cycles ngẫu nhiên (tốt cho demo/monitoring):
```bash
python producer.py --continuous [n]
```

**Examples:**
```bash
python producer.py --continuous      # 10 cycles (default)
python producer.py --continuous 5    # 5 cycles
python producer.py --continuous 100  # 100 cycles
```

**Features:**
- Random cycle selection (diverse data)
- Perfect for real-time monitoring demo
- Good for testing anomaly detection

**Time:** ~60 seconds × n + 2 seconds pause

---

## Complete Examples

### Quick Test (1 cycle)
```bash
cd src
source ../venv/bin/activate
python producer.py 0
```

### Short Demo (10 cycles)
```bash
cd src
python producer.py 0 10
# Or random cycles:
python producer.py --continuous 10
```

### Extended Demo (100 cycles - ~2 hours)
```bash
cd src
python producer.py --continuous 100
```

### First 500 cycles (~8.5 hours)
```bash
cd src
python producer.py 0 500
```

### All Data (Production run)
```bash
cd src
# Run in background with nohup
nohup python producer.py --all > producer_all.log 2>&1 &

# Monitor progress
tail -f producer_all.log
```

---

## Performance Metrics

| Mode | Cycles | Messages | Time | Use Case |
|------|--------|----------|------|----------|
| Single | 1 | 43,680 | 1 min | Quick test |
| Range (10) | 10 | 436,800 | 10 min | Demo |
| Continuous (10) | 10 random | 436,800 | 10 min | Monitoring demo |
| Range (100) | 100 | 4,368,000 | 100 min | Extended test |
| All | 2,205 | 96,314,400 | 2,205 min | Full dataset |

---

## With Consumer

Always start consumer BEFORE producer:

### Terminal 1: Consumer
```bash
cd src
python consumer.py prometheus
# Or for MongoDB:
python consumer.py mongodb
```

### Terminal 2: Producer
```bash
cd src
# Choose your mode:
python producer.py 0              # Single
python producer.py 0 10           # Range
python producer.py --continuous 5 # Continuous
```

---

## Tips

1. **Start small:** Test với 1-10 cycles trước
2. **Monitor resources:** Check CPU, memory, disk khi chạy nhiều cycles
3. **Background mode:** Dùng `nohup` cho runs dài
4. **Logs:** Redirect output ra file cho debugging

---

## Troubleshooting

### Kafka not ready
```bash
# Wait for Kafka to start
sleep 10
# Or restart Kafka
docker-compose -f docker-compose.khang.yml restart kafka
```

### Out of memory
```bash
# Reduce batch size or run fewer cycles
python producer.py 0 10  # Instead of --all
```

### Data not showing in Grafana
```bash
# Check consumer is running
ps aux | grep consumer.py

# Restart consumer
pkill -f "consumer.py prometheus"
python consumer.py prometheus &

# Verify metrics
curl http://localhost:9091/metrics | grep hydraulic
```


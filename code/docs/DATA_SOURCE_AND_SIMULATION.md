# 📊 Nguồn Dữ Liệu & Mô Phỏng Real-time Streaming

Tài liệu trình bày về nguồn dữ liệu và cách setup mô phỏng dữ liệu để bắn vào Kafka.

---

## 1. 📁 Nguồn Dữ Liệu (Data Source)

### 1.1. Dataset Overview

**Tên dataset:** Condition Monitoring of Hydraulic Systems

**Nguồn:**
- **Creator:** ZeMA gGmbH, Eschberger Weg 46, 66121 Saarbrücken, Germany
- **Contact:** t.schneider@zema.de, s.klein@zema.de
- **Năm:** 2018

**Đặc điểm:**
- **Loại:** Multivariate Time-Series
- **Số cycles:** 2,205 cycles
- **Thời gian mỗi cycle:** 60 giây
- **Tổng số attributes:** 43,680 (8×60 + 2×600 + 7×6,000)
- **Missing values:** Không có

### 1.2. Hệ Thống Thủy Lực (Hydraulic Test Rig)

**Cấu trúc hệ thống:**
```
Primary Working Circuit ←→ Oil Tank ←→ Secondary Cooling-Filtration Circuit
```

**Chức năng:**
- Hệ thống thực hiện các chu kỳ tải trọng không đổi (60 giây/cycle)
- Đo các giá trị quá trình: áp suất, lưu lượng thể tích, nhiệt độ
- Thay đổi điều kiện của 4 thành phần thủy lực:
  1. **Cooler** (Bộ làm mát)
  2. **Valve** (Van)
  3. **Pump** (Bơm)
  4. **Accumulator** (Bình tích áp)

### 1.3. 17 Sensors & Sampling Rates

| Sensor | Tên đầy đủ | Đại lượng vật lý | Đơn vị | Tần số lấy mẫu | Số mẫu/cycle |
|--------|------------|------------------|--------|----------------|--------------|
| **PS1-6** | Pressure Sensor 1-6 | Áp suất | bar | **100 Hz** | 6,000 |
| **EPS1** | Motor Power | Công suất động cơ | W | **100 Hz** | 6,000 |
| **FS1-2** | Flow Sensor 1-2 | Lưu lượng thể tích | l/min | **10 Hz** | 600 |
| **TS1-4** | Temperature Sensor 1-4 | Nhiệt độ | °C | **1 Hz** | 60 |
| **VS1** | Vibration Sensor | Rung động | mm/s | **1 Hz** | 60 |
| **CE** | Cooling Efficiency | Hiệu suất làm mát (ảo) | % | **1 Hz** | 60 |
| **CP** | Cooling Power | Công suất làm mát (ảo) | kW | **1 Hz** | 60 |
| **SE** | Efficiency Factor | Hệ số hiệu suất | % | **1 Hz** | 60 |

**Tổng số messages/cycle:** 43,680 messages
- 7 sensors × 6,000 = 42,000 (100Hz)
- 2 sensors × 600 = 1,200 (10Hz)
- 8 sensors × 60 = 480 (1Hz)

### 1.4. Cấu Trúc File Dữ Liệu

**Định dạng:**
- **File:** `data/PS1.txt`, `data/PS2.txt`, ..., `data/SE.txt`
- **Format:** Tab-delimited (tab-separated values)
- **Cấu trúc:**
  ```
  Row 0:   191.44  178.41  191.38  ...  151.19  [6000 values]
  Row 1:   192.11  179.22  192.05  ...  152.33  [6000 values]
  ...
  Row 2204: 185.67  174.89  185.61  ...  145.12  [6000 values]
  ```
- **Mỗi dòng = 1 cycle** (60 giây dữ liệu)
- **Mỗi cột = 1 sample** tại thời điểm cụ thể trong cycle

**Ví dụ với PS1.txt (100Hz):**
- Dòng 0: 6,000 giá trị áp suất (mỗi 0.01 giây)
- Dòng 1: 6,000 giá trị áp suất của cycle tiếp theo
- ...

**Ví dụ với TS1.txt (1Hz):**
- Dòng 0: 60 giá trị nhiệt độ (mỗi 1 giây)
- Dòng 1: 60 giá trị nhiệt độ của cycle tiếp theo
- ...

### 1.5. Condition Labels (profile.txt)

File `data/profile.txt` chứa nhãn điều kiện cho mỗi cycle:

| Cột | Thành phần | Giá trị | Ý nghĩa |
|-----|------------|---------|---------|
| 1 | Cooler condition | 3, 20, 100 | 3: gần hỏng, 20: giảm hiệu suất, 100: hiệu suất đầy đủ |
| 2 | Valve condition | 73, 80, 90, 100 | 100: tối ưu, 90: lag nhỏ, 80: lag lớn, 73: gần hỏng |
| 3 | Pump leakage | 0, 1, 2 | 0: không rò, 1: rò nhẹ, 2: rò nặng |
| 4 | Accumulator pressure | 90, 100, 115, 130 | 130: tối ưu, 115: giảm nhẹ, 100: giảm nặng, 90: gần hỏng |
| 5 | Stable flag | 0, 1 | 0: ổn định, 1: chưa ổn định |

---

## 2. 🔧 Setup Mô Phỏng Dữ Liệu Real-time

### 2.1. Kiến Trúc Mô Phỏng

```
┌─────────────────┐
│  Data Files     │  17 files (PS1-6, EPS1, FS1-2, TS1-4, CE, CP, SE, VS1)
│  (2,205 cycles) │  Tab-delimited format
└────────┬────────┘
         │
         v
┌─────────────────────────────┐
│  Kafka Producer             │  Multi-threaded (17 threads)
│  (producer.py)              │  - Đọc từ file
│                             │  - Mô phỏng timing chính xác
│                             │  - Gửi vào Kafka topics
└────────┬────────────────────┘
         │
         v
┌─────────────────────────────┐
│  Kafka Cluster              │  17 topics (1 topic/sensor)
│  (localhost:29092)          │  - hydraulic-PS1
│                             │  - hydraulic-PS2
│                             │  - ... (17 topics)
└─────────────────────────────┘
```

### 2.2. Producer Design

**File:** `src/producer.py`

**Thiết kế:**
- **Multi-threaded:** 17 threads độc lập, mỗi thread xử lý 1 sensor
- **Accurate timing:** Sử dụng `time.sleep()` với interval chính xác theo sampling rate
- **Real-time simulation:** Gửi dữ liệu đúng tần số như trong thực tế

**Cấu hình sensors:**
```python
SENSOR_CONFIGS = {
    # Pressure sensors (100Hz)
    "PS1": ("PS1.txt", 100, 6000),  # filename, Hz, samples/cycle
    "PS2": ("PS2.txt", 100, 6000),
    # ... PS3-6
    "EPS1": ("EPS1.txt", 100, 6000),  # Motor power
    
    # Flow sensors (10Hz)
    "FS1": ("FS1.txt", 10, 600),
    "FS2": ("FS2.txt", 10, 600),
    
    # Temperature sensors (1Hz)
    "TS1": ("TS1.txt", 1, 60),
    # ... TS2-4
    
    # Other sensors (1Hz)
    "VS1": ("VS1.txt", 1, 60),  # Vibration
    "CE": ("CE.txt", 1, 60),    # Cooling efficiency
    "CP": ("CP.txt", 1, 60),    # Cooling power
    "SE": ("SE.txt", 1, 60),    # Efficiency factor
}
```

**Timing logic:**
```python
# Tính interval giữa các samples
interval = 1.0 / sampling_rate_hz  # 0.01s cho 100Hz, 0.1s cho 10Hz, 1.0s cho 1Hz

for idx, value in enumerate(data):
    # Tính thời gian mong đợi cho sample này
    expected_time = start_time + (idx * interval)
    
    # Sleep đến đúng thời điểm
    sleep_time = expected_time - time.time()
    if sleep_time > 0:
        time.sleep(sleep_time)
    
    # Gửi message vào Kafka
    producer.send(topic, value=message)
```

### 2.3. Message Format

**JSON structure:**
```json
{
  "sensor": "PS1",
  "cycle": 0,
  "sample_idx": 100,
  "value": 151.19,
  "timestamp": "2025-11-08T14:30:45.123456",
  "sampling_rate_hz": 100
}
```

**Kafka topic:** `hydraulic-{sensor_name}`
- Ví dụ: `hydraulic-PS1`, `hydraulic-TS1`, `hydraulic-FS1`

### 2.4. Cách Sử Dụng Producer

#### **1. Single Cycle (1 cycle - 60 giây)**
```bash
cd src
python producer.py 0  # Chạy cycle đầu tiên
```

#### **2. Range of Cycles (nhiều cycles liên tiếp)**
```bash
python producer.py 0 10    # Chạy cycles 0-9 (10 cycles, ~10 phút)
python producer.py 0 100   # Chạy 100 cycles đầu (~100 phút)
```

#### **3. Continuous Mode (cycles ngẫu nhiên)**
```bash
python producer.py --continuous 10  # 10 cycles ngẫu nhiên (~10 phút)
```

#### **4. All Cycles (toàn bộ dataset)**
```bash
python producer.py --all  # 2,205 cycles (~36.75 giờ)
```

### 2.5. Workflow Setup

**Bước 1: Start Kafka & Services**
```bash
# Start Docker services (Kafka, Zookeeper, Prometheus, Grafana)
bash scripts/setup_prometheus.sh

# Hoặc dùng docker-compose
docker-compose -f docker-compose.khang.yml up -d
```

**Bước 2: Start Consumer (Terminal 1)**
```bash
cd src
source ../venv/bin/activate
python consumer.py prometheus
```

**Bước 3: Start Producer (Terminal 2)**
```bash
cd src
source ../venv/bin/activate

# Chọn mode:
python producer.py 0              # Single cycle
python producer.py 0 10           # 10 cycles
python producer.py --continuous 5 # 5 cycles ngẫu nhiên
```

**Bước 4: Xem Dashboard**
- Mở Grafana: http://localhost:3000
- Dashboard tự động refresh mỗi 5 giây

### 2.6. Performance Metrics

| Mode | Cycles | Messages | Thời gian | Use Case |
|------|--------|----------|-----------|----------|
| Single | 1 | 43,680 | 1 phút | Quick test |
| Range (10) | 10 | 436,800 | 10 phút | Demo |
| Continuous (10) | 10 random | 436,800 | 10 phút | Monitoring demo |
| Range (100) | 100 | 4,368,000 | 100 phút | Extended test |
| All | 2,205 | 96,314,400 | 2,205 phút (~37h) | Full dataset |

### 2.7. Đặc Điểm Kỹ Thuật

**1. Multi-threading:**
- 17 threads chạy song song
- Mỗi thread độc lập, không block nhau
- Đảm bảo timing chính xác cho từng sensor

**2. Timing Accuracy:**
- Sử dụng `time.time()` để tính toán chính xác
- Sleep đến đúng thời điểm mong đợi
- Compensate cho processing time

**3. Kafka Connection:**
- Retry logic (5 lần) nếu Kafka chưa sẵn sàng
- Auto-reconnect khi mất kết nối
- Batch sending với `acks=1` (performance)

**4. Data Loading:**
- Load toàn bộ cycle data vào memory trước
- Parse tab-delimited values
- Validate cycle index

### 2.8. Demo Scripts

**Quick Test (1 cycle):**
```bash
./scripts/quick_test.sh
```

**Continuous Demo (10 cycles):**
```bash
./scripts/demo_realtime.sh
```

---

## 3. 📈 Tóm Tắt

### Nguồn Dữ Liệu:
- ✅ Dataset từ ZeMA gGmbH (Germany)
- ✅ 2,205 cycles × 60 giây = 132,300 giây dữ liệu
- ✅ 17 sensors với 3 tần số lấy mẫu khác nhau (1Hz, 10Hz, 100Hz)
- ✅ Tổng 43,680 samples/cycle = 96.3M messages toàn bộ dataset

### Mô Phỏng Real-time:
- ✅ Multi-threaded producer (17 threads)
- ✅ Timing chính xác theo sampling rate
- ✅ Gửi vào 17 Kafka topics riêng biệt
- ✅ Hỗ trợ nhiều modes: single, range, continuous, all
- ✅ Real-time streaming với Kafka → Consumer → Prometheus → Grafana

### Use Cases:
- ✅ Real-time monitoring dashboard
- ✅ Anomaly detection testing
- ✅ System performance testing
- ✅ Demo & presentation

---

## 📚 References

1. **Dataset Paper:**
   - Nikolai Helwig, Eliseo Pignanelli, Andreas Schütze, "Condition Monitoring of a Complex Hydraulic System Using Multivariate Statistics", I2MTC-2015, Pisa, Italy, 2015.

2. **Dataset Source:**
   - ZeMA gGmbH, Eschberger Weg 46, 66121 Saarbrücken, Germany
   - Contact: t.schneider@zema.de

3. **Project Documentation:**
   - `docs/SETUP.md` - Hướng dẫn setup chi tiết
   - `docs/ARCHITECTURE.md` - Kiến trúc hệ thống
   - `docs/PRODUCER_USAGE.md` - Hướng dẫn sử dụng producer


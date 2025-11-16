# 📊 Sensor Data Files

Thư mục này chứa dữ liệu từ 17 sensors của hydraulic test rig.

## 📁 Required Files

Dựa trên cấu hình trong `src/producer.py`, cần các file sau:

### Pressure Sensors (100Hz - 6000 samples/cycle)

- `PS1.txt` - Pressure sensor 1
- `PS2.txt` - Pressure sensor 2
- `PS3.txt` - Pressure sensor 3
- `PS4.txt` - Pressure sensor 4
- `PS5.txt` - Pressure sensor 5
- `PS6.txt` - Pressure sensor 6

### Motor Power (100Hz - 6000 samples/cycle)

- `EPS1.txt` - Motor power sensor

### Volume Flow Sensors (10Hz - 600 samples/cycle)

- `FS1.txt` - Flow sensor 1
- `FS2.txt` - Flow sensor 2

### Temperature Sensors (1Hz - 60 samples/cycle)

- `TS1.txt` - Temperature sensor 1
- `TS2.txt` - Temperature sensor 2
- `TS3.txt` - Temperature sensor 3
- `TS4.txt` - Temperature sensor 4

### Vibration Sensor (1Hz - 60 samples/cycle)

- `VS1.txt` - Vibration sensor

### Virtual Sensors (1Hz - 60 samples/cycle)

- `CE.txt` - Cooling efficiency
- `CP.txt` - Cooling power
- `SE.txt` - System efficiency

## 📋 File Format

Mỗi file chứa **2,205 cycles** của dữ liệu:

- Mỗi dòng = 1 cycle
- Giá trị phân cách bằng tab (`\t`)
- Số lượng giá trị mỗi dòng tùy theo sampling rate:
  - 100Hz sensors: 6000 values/cycle
  - 10Hz sensors: 600 values/cycle
  - 1Hz sensors: 60 values/cycle

### Example Format (PS1.txt):

```
191.44	178.41	191.38	...	151.19	[6000 values]
192.15	179.22	192.09	...	152.01	[6000 values]
...
[2205 lines total]
```

## 🚀 Usage

Producer sẽ tự động đọc các file này từ thư mục `data/`:

```bash
cd src
python producer.py 0  # Read cycle 0 from all files
```

## ⚠️ Note

- Các file này **không được commit vào git** (đã có trong `.gitignore`)
- File size: ~10-50MB mỗi file (tùy sensor)
- Tổng size: ~500MB - 2GB cho toàn bộ dataset
- Cần download dataset từ nguồn gốc và đặt vào thư mục này

## 📥 Getting Data

Nếu chưa có data files, cần:

1. Download dataset từ nguồn gốc
2. Đặt các file `.txt` vào thư mục `data/`
3. Đảm bảo format đúng (tab-delimited, đúng số lượng values/cycle)

---

**Total:** 17 sensor files × 2,205 cycles = **~96.3 million data points**

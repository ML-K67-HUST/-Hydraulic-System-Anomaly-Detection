# 📊 Data Source & Real-time Streaming Simulation
## Slide Presentation - Detailed Explanation

---

## Slide 1: Problem Statement

### Why do we need to simulate real-time data?

**Real-world challenges:**
- Real hydraulic system data is expensive and hard to obtain
- Need to test monitoring system before deployment
- Need to demo real-time system for clients/instructors

**Solution:**
- Use existing dataset from laboratory
- Simulate real-time data transmission like real system
- Create continuous data stream for testing and demo

**Result:**
- Can test monitoring system with real data
- Can demo real-time system without actual equipment

---

## Slide 2: Data Source - Dataset

### Dataset: Condition Monitoring of Hydraulic Systems

**Origin:**
- From **ZeMA gGmbH** laboratory in Germany (2018)
- This is real data from hydraulic system in laboratory
- Published publicly for research

**Dataset characteristics:**
- **2,205 cycles** = 2,205 test runs
- **Each cycle = 60 seconds** = 1 minute of data
- **Total duration:** 2,205 × 60 seconds = 132,300 seconds = **36.75 hours** of real data
- **No missing data** = complete dataset, ready to use

**Why use this dataset?**
- Real data from industrial system
- Large enough to test system (2,205 cycles)
- Has condition labels (good/bad) to test anomaly detection

---

## Slide 3: Real Hydraulic System

### Hydraulic Test Rig - Test System

**System structure:**
```
Primary Working Circuit ←→ Oil Tank ←→ Secondary Cooling-Filtration Circuit
```

**Explanation:**
- This is a real hydraulic system in laboratory
- Has 2 circuits: main circuit (working) and secondary circuit (cooling)
- Connected via shared oil tank

**What does the system do?**
1. **Run load cycles:** Every 60 seconds performs 1 work cycle
2. **Measure parameters:** Pressure, oil flow rate, temperature
3. **Change conditions:** Intentionally degrade/reduce efficiency of 4 components:
   - **Cooler** - reduced cooling efficiency
   - **Valve** - slow operation/lag
   - **Pump** - leakage
   - **Accumulator** - reduced pressure

**Purpose:** Collect data when system is normal and when it has faults for research

---

## Slide 4: 17 Sensors - Measurement Sensors

### Why so many sensors?

**Each sensor measures different parameter:**
- To fully understand system state
- Detect faults from multiple angles
- Ensure safety and efficiency

### 3 Sensor Groups by Sampling Frequency

**Sampling frequency = Number of measurements per second**

| Frequency | Sensors | Measurements/sec | Samples in 60s | Why? |
|-----------|----------|------------------|----------------|------|
| **100 Hz** | PS1-6, EPS1 (7 sensors) | 100 times | 6,000 samples | Pressure changes fast, need high frequency |
| **10 Hz** | FS1-2 (2 sensors) | 10 times | 600 samples | Flow rate changes slower |
| **1 Hz** | TS1-4, VS1, CE, CP, SE (8 sensors) | 1 time | 60 samples | Temperature/vibration changes very slowly |

**Easy to understand example:**
- **100 Hz** = Measure pressure 100 times/second (every 0.01s) → Need high accuracy
- **1 Hz** = Measure temperature 1 time/second → Temperature changes slowly, don't need high frequency

**Total:** 17 sensors → **43,680 data samples in 1 cycle (60 seconds)**

---

## Slide 5: Detailed Sensor Types

### 100 Hz Sensors - Fast Sampling (6,000 samples/cycle)

**PS1-6: Pressure Sensors**
- Measure oil pressure at 6 different locations
- Unit: **bar** (1 bar ≈ 1 atm)
- Why need fast sampling? Pressure changes very quickly when pump operates

**EPS1: Motor Power**
- Measure power consumption of pump motor
- Unit: **Watt (W)**
- Why need fast sampling? Power changes with load

### 10 Hz Sensors - Medium Sampling (600 samples/cycle)

**FS1-2: Flow Sensors**
- Measure oil flow rate
- Unit: **liters/minute (l/min)**
- Why slower? Flow rate changes slower than pressure

### 1 Hz Sensors - Slow Sampling (60 samples/cycle)

**TS1-4: Temperature Sensors**
- Measure oil temperature at 4 locations
- Unit: **°C**
- Why slowest? Temperature changes very slowly

**VS1: Vibration Sensor**
- Measure system vibration
- Unit: **mm/s**

**CE, CP, SE: Virtual Sensors**
- Not real sensors, calculated from other data
- CE: Cooling efficiency (%)
- CP: Cooling power (kW)
- SE: Efficiency factor (%)

---

## Slide 6: Data File Structure - How is Data Stored?

### Format: Tab-delimited (Tab-separated)

**Example file PS1.txt (Pressure sensor 1):**

```
Row 0:   191.44  178.41  191.38  ...  151.19  [6000 numbers]
Row 1:   192.11  179.22  192.05  ...  152.33  [6000 numbers]
Row 2:   193.45  180.12  193.38  ...  153.67  [6000 numbers]
...
Row 2204: 185.67  174.89  185.61  ...  145.12  [6000 numbers]
```

**Explanation:**
- **Each row = 1 cycle** = 60 seconds of data
- **Each number in row = 1 measurement** at specific time point
- **Row 0** = First cycle, **Row 2204** = Last cycle
- **6000 numbers** = 6000 measurements in 60 seconds (because sampling at 100 times/second)

**Concrete example:**
- Row 0, first number (191.44) = Pressure at second 0.00
- Row 0, second number (178.41) = Pressure at second 0.01
- Row 0, 100th number (e.g., 185.23) = Pressure at second 1.00
- ...

**17 files corresponding to 17 sensors:**
- `PS1.txt` → `PS6.txt`: 6 pressure sensors
- `EPS1.txt`: Motor power
- `FS1.txt`, `FS2.txt`: 2 flow sensors
- `TS1.txt` → `TS4.txt`: 4 temperature sensors
- `VS1.txt`: Vibration sensor
- `CE.txt`, `CP.txt`, `SE.txt`: 3 virtual sensors

---

## Slide 7: Condition Labels

### File: profile.txt - System State Notes

**Each row in file = 1 cycle, records state of 4 components:**

| Column | Component | Possible Values | Meaning |
|--------|-----------|-----------------|---------|
| 1 | **Cooler** | 3, 20, 100 | 100: Good cooling<br>20: Reduced cooling<br>3: Near failure |
| 2 | **Valve** | 73, 80, 90, 100 | 100: Optimal operation<br>90: Slight lag<br>80: Severe lag<br>73: Near failure |
| 3 | **Pump** | 0, 1, 2 | 0: No leakage<br>1: Weak leakage<br>2: Severe leakage |
| 4 | **Accumulator** | 90, 100, 115, 130 | 130: Optimal pressure<br>115: Slightly reduced<br>100: Severely reduced<br>90: Near failure |
| 5 | **Stable flag** | 0, 1 | 0: System stable<br>1: Not yet stable |

**Example:**
```
Cycle 0:  100  100  0  130  0  → All good
Cycle 100: 20   90  1  115  0  → Cooler poor, Valve slight lag, Pump weak leakage
Cycle 500: 3    73  2   90  1  → Near failure, not stable
```

**Why need this file?**
- To know which cycles are normal, which have faults
- Use to train/test fault detection models
- To validate monitoring results

---

## Slide 8: Challenge - How to Simulate Real-time?

### Challenges

**Current data:**
- Stored in static files (not moving)
- All data already available (not real-time)
- Need to "simulate" sending data like real system

**Requirements:**
- Send data at correct frequency like real system (100Hz, 10Hz, 1Hz)
- Send continuously, without interruption
- 17 sensors send simultaneously, don't wait for each other

**Solution:**
- Read data from files
- Calculate timing accurately
- Send to Kafka with correct timing
- Use multi-threading to send in parallel

---

## Slide 9: Simulation Architecture - Data Flow

### From Static Files → Real-time Streaming

```
┌─────────────────────────────────┐
│  Data Files (Static)            │
│  - 17 files (.txt)              │
│  - 2,205 cycles per file        │
│  - Tab-delimited format         │
└────────────┬────────────────────┘
             │
             │ Read and process
             ▼
┌─────────────────────────────────┐
│  Kafka Producer                 │
│  (producer.py)                  │
│  - Read each cycle from file    │
│  - Calculate accurate timing     │
│  - Send to Kafka                │
│  - 17 threads (1 thread/sensor)│
└────────────┬────────────────────┘
             │
             │ Send messages
             ▼
┌─────────────────────────────────┐
│  Kafka Cluster                  │
│  (localhost:29092)              │
│  - 17 separate topics           │
│  - hydraulic-PS1, PS2, ..., SE  │
│  - Store messages                │
└─────────────────────────────────┘
```

**Step-by-step explanation:**

1. **Data Files:** Static data in files, not moving yet
2. **Producer:** Read files, calculate timing, send to Kafka
3. **Kafka:** Receive and store messages, create real-time data stream

**Why use Kafka?**
- Kafka is popular message queue system
- Can handle many messages simultaneously
- Consumer can read data in real-time

---

## Slide 10: Producer Design - Detailed Design

### Multi-threaded Architecture - Multiple Processing Threads

**Problem:** 17 sensors need to send simultaneously, each sensor has different frequency

**Solution:** Use 17 independent threads

**How it works:**
```
Thread 1: PS1 (100Hz)  → Send 100 messages/second
Thread 2: PS2 (100Hz)  → Send 100 messages/second
...
Thread 7: EPS1 (100Hz) → Send 100 messages/second
Thread 8: FS1 (10Hz)   → Send 10 messages/second
Thread 9: FS2 (10Hz)   → Send 10 messages/second
Thread 10: TS1 (1Hz)   → Send 1 message/second
...
Thread 17: SE (1Hz)    → Send 1 message/second
```

**Why need multi-threading?**
- If use 1 thread: Must send sequentially → Incorrect timing
- Use 17 threads: Each sensor manages its own timing → Accurate

---

## Slide 11: Timing Logic - How to Ensure Accurate Timing?

### Time Calculation Method

**Example with 100Hz sensor (PS1):**
- Must send 100 messages in 1 second
- Interval between 2 messages = 1/100 = **0.01 seconds**

**Code logic:**
```python
# Calculate interval between messages
interval = 1.0 / sampling_rate_hz
# 100Hz → 0.01s
# 10Hz  → 0.1s
# 1Hz   → 1.0s

# Record start time
start_time = time.time()

# For each value in data
for idx, value in enumerate(data):
    # Calculate expected time for this message
    expected_time = start_time + (idx * interval)
    # Example: 100th message → expected_time = start + 100 × 0.01 = start + 1.0s
    
    # Calculate sleep time needed
    sleep_time = expected_time - time.time()
    # If time remaining → sleep
    if sleep_time > 0:
        time.sleep(sleep_time)
    
    # Send message to Kafka
    producer.send(topic, message)
```

**Concrete example (PS1, 100Hz):**
- T=0.00s: Send message 1 (value = 191.44)
- T=0.01s: Send message 2 (value = 178.41)
- T=0.02s: Send message 3 (value = 191.38)
- ...
- T=1.00s: Send message 100
- T=60.00s: Send message 6000 (cycle complete)

**Why need such complex calculation?**
- Ensure sending at correct time, not too fast or slow
- Compensate for code processing time
- Similar to real system

---

## Slide 12: Message Format - Data Structure Sent

### JSON Structure - Data Format

**Each message sent to Kafka has format:**

```json
{
  "sensor": "PS1",                    // Sensor name
  "cycle": 0,                          // Which cycle (0-2204)
  "sample_idx": 100,                   // Which sample in cycle (0-5999)
  "value": 151.19,                     // Measured value
  "timestamp": "2025-11-08T14:30:45.123456",  // Send time
  "sampling_rate_hz": 100             // Sampling frequency (100Hz)
}
```

**Field explanations:**
- **sensor:** To know which sensor this message is from
- **cycle:** To know which cycle (can use for analysis)
- **sample_idx:** Position in cycle (0 = start of cycle, 5999 = end of cycle)
- **value:** Actual value (e.g., 151.19 bar)
- **timestamp:** Send time (to know when sent)
- **sampling_rate_hz:** Frequency to know if sensor is fast or slow

**Real example:**
```json
// Message from PS1, cycle 0, sample 100
{
  "sensor": "PS1",
  "cycle": 0,
  "sample_idx": 100,
  "value": 185.23,
  "timestamp": "2025-11-08T14:30:46.000000",
  "sampling_rate_hz": 100
}
```

**Kafka Topics:**
- Each sensor has its own topic
- `hydraulic-PS1`, `hydraulic-PS2`, ..., `hydraulic-SE`
- Total 17 topics

**Why separate topics?**
- Easy to process: Consumer can subscribe to specific sensor
- Better performance: Don't need to filter messages
- Clear data organization

---

## Slide 13: Producer Usage - 4 Modes

### 1. Single Cycle - Run 1 Cycle

**Command:**
```bash
python producer.py 0
```

**What it does:**
- Run cycle 0 (first cycle)
- Send 43,680 messages (1 cycle)
- Takes about **60 seconds** (1 minute)

**When to use:**
- Quick system test
- Check if producer is working

---

### 2. Range - Run Multiple Consecutive Cycles

**Command:**
```bash
python producer.py 0 10
```

**What it does:**
- Run from cycle 0 to cycle 9 (10 cycles)
- Send 436,800 messages (10 × 43,680)
- Takes about **10 minutes** (10 × 60 seconds)

**When to use:**
- Short demo
- Test with multiple cycles
- Check system with diverse data

---

### 3. Continuous - Run Random Cycles

**Command:**
```bash
python producer.py --continuous 10
```

**What it does:**
- Randomly select 10 cycles from 2,205 cycles
- Run those 10 cycles sequentially
- Takes about **10 minutes**

**When to use:**
- Real-time monitoring demo
- Test with diverse data (not just first cycles)
- Suitable for presentation

**Advantages:**
- More diverse data (not just first cycles)
- More like real-time (don't know which cycle in advance)

---

### 4. All - Run Entire Dataset

**Command:**
```bash
python producer.py --all
```

**What it does:**
- Run all 2,205 cycles
- Send 96,314,400 messages (2,205 × 43,680)
- Takes about **36.75 hours** (2,205 minutes)

**When to use:**
- Batch processing entire dataset
- Test system with full data
- Not for demo (too long!)

**Note:**
- Runs very long (almost 2 days)
- Need to ensure system stability
- Should run in background with `nohup`

---

## Slide 14: Workflow Setup - System Run Procedure

### Step 1: Start Services

**Command:**
```bash
bash scripts/setup_prometheus.sh
```

**What it does:**
- Start Docker containers:
  - **Kafka** (message queue)
  - **Zookeeper** (Kafka management)
  - **Prometheus** (time-series storage)
  - **Pushgateway** (receive metrics from consumer)
  - **Grafana** (visualization)

**Check:**
- Wait 30-60 seconds for services to start
- Check: `docker ps` → See containers running

---

### Step 2: Start Consumer (Terminal 1)

**Command:**
```bash
cd src
python consumer.py prometheus
```

**What it does:**
- Consumer reads messages from Kafka
- Convert to Prometheus format
- Send to Pushgateway
- Pushgateway → Prometheus stores

**Why need consumer?**
- Kafka only stores messages
- Need consumer to read and process
- Consumer converts format for Prometheus

**Note:**
- Must run BEFORE producer
- To be ready to receive messages when producer sends

---

### Step 3: Start Producer (Terminal 2)

**Command:**
```bash
cd src
python producer.py 0 10  # Run 10 cycles
```

**What it does:**
- Read data from files
- Send messages to Kafka with accurate timing
- 17 threads run in parallel

**When does it start sending?**
- Immediately after running command
- Sends continuously for 10 minutes (10 cycles × 60s)

---

### Step 4: View Dashboard

**Open browser:**
- URL: **http://localhost:3000**
- Username: `admin`
- Password: `admin`

**Dashboard:**
- Automatically has "Hydraulic System - Prometheus" dashboard
- Displays real-time data from 17 sensors
- Auto-refreshes every 5 seconds

**What to see:**
- Charts for pressure, temperature, flow rate
- Real-time values from each sensor
- Anomaly detection (if any)

---

## Slide 15: Performance Metrics

### Comparison Table of Modes

| Mode | Cycles | Messages | Duration | When to use? |
|------|--------|----------|----------|--------------|
| **Single** | 1 | 43,680 | 1 minute | Quick test |
| **Range (10)** | 10 | 436,800 | 10 minutes | Short demo |
| **Continuous (10)** | 10 random | 436,800 | 10 minutes | Monitoring demo |
| **Range (100)** | 100 | 4.4 million | 100 minutes | Extended test |
| **All** | 2,205 | 96.3 million | 37 hours | Batch processing |

**Explanation:**
- **Messages:** Total messages sent to Kafka
- **Duration:** Producer run time (≈ number of cycles × 60s)
- **Use case:** Suitable situation to use

**Calculation example:**
- 1 cycle = 60s = 43,680 messages
- 10 cycles = 600s = 10 minutes = 436,800 messages
- 2,205 cycles = 132,300s = 36.75 hours = 96,314,400 messages

---

## Slide 16: Technical Features - Why Design This Way?

### 1. Multi-threading - Multiple Processing Threads

**Problem:** 17 sensors need to send simultaneously, each sensor has different timing

**Solution:** 17 independent threads

**Benefits:**
- Each sensor manages its own timing → Accurate
- Don't block each other → High performance
- Easy to extend (add sensor = add thread)

**Comparison:**
- ❌ 1 thread: Must send sequentially → Incorrect timing
- ✅ 17 threads: Send in parallel → Correct timing

---

### 2. Timing Accuracy - Time Precision

**Problem:** Must send at correct time (e.g., every 0.01s for 100Hz)

**Solution:** Calculate expected time and sleep

**How:**
- Record start time
- Calculate expected time for each message
- Sleep until correct time
- Compensate for code processing time

**Benefits:**
- Send at correct frequency like real system
- Not too fast or slow
- Similar to real system

---

### 3. Kafka Connection

**Problem:** Kafka may not be ready when producer starts

**Solution:** Retry logic

**How:**
- Try to connect to Kafka
- If fail → Wait 2 seconds, retry
- Try maximum 5 times
- If still fail → Report error

**Benefits:**
- Automatic retry → No manual intervention needed
- Wait for Kafka to start → Auto-connect
- More robust

---

### 4. Data Loading

**Problem:** Need to read data from files quickly

**Solution:** Load entire cycle into memory

**How:**
- Read file once
- Parse tab-delimited → List of numbers
- Store in memory
- Reuse when sending

**Benefits:**
- Fast (don't need to read file multiple times)
- Simple (data ready in memory)
- High performance

---

## Slide 17: Summary - Key Points

### Data Source

✅ **Real dataset** from German laboratory (ZeMA gGmbH)  
✅ **2,205 cycles** × 60 seconds = 36.75 hours of real data  
✅ **17 sensors** with 3 different frequencies (1Hz, 10Hz, 100Hz)  
✅ **43,680 samples/cycle** = 96.3 million messages for entire dataset  
✅ **Has condition labels** to test anomaly detection

### Real-time Simulation

✅ **Multi-threaded producer** (17 threads) - Send in parallel  
✅ **Accurate timing** - Correct frequency like real system  
✅ **17 Kafka topics** - Clear data organization  
✅ **Real-time streaming** → Consumer → Prometheus → Grafana  
✅ **4 modes** - From quick test to batch processing

### Use Cases - Applications

✅ **Real-time monitoring** - Monitor system in real-time  
✅ **Anomaly detection** - Detect faults with labeled data  
✅ **System testing** - Test system with real data  
✅ **Demo & presentation** - Demo system for clients/instructors

---

## Slide 18: Conclusion

### What We Achieved?

1. **Have real data** from industrial system
2. **Can simulate real-time** like real system
3. **Can test system** monitoring before deployment
4. **Can demo** for clients/instructors

### Benefits

- ✅ Don't need real equipment (expensive, hard to get)
- ✅ Can test with many scenarios (2,205 cycles)
- ✅ Data has labels (know which cycles have faults)
- ✅ Can run multiple times (reproducible)

### Future Development

- Add new sensors
- Integrate ML models for fault detection
- Extend to other systems
- Optimize performance

---

## Slide 19: References

### 1. Dataset Paper

**Helwig et al., "Condition Monitoring of a Complex Hydraulic System Using Multivariate Statistics"**
- Conference: I2MTC-2015, Pisa, Italy
- Detailed description of dataset and system
- Data analysis methods

### 2. Dataset Source

**ZeMA gGmbH, Saarbrücken, Germany**
- Research organization in Germany
- Contact: t.schneider@zema.de
- Dataset publicly available for research

### 3. Project Documentation

- **`docs/SETUP.md`** - Detailed setup guide
- **`docs/ARCHITECTURE.md`** - System architecture
- **`docs/PRODUCER_USAGE.md`** - Producer usage guide
- **`docs/DATA_SOURCE_AND_SIMULATION.md`** - This document

---

## Slide 20: Q&A - Frequently Asked Questions

### Q1: Why not use real data?

**A:** Real data is very expensive, requires specialized equipment. This dataset is real data from laboratory, sufficient for testing and demo.

### Q2: Why need to simulate real-time?

**A:** To test monitoring system like in real world. If only read static files, not like real-time.

### Q3: Why use Kafka?

**A:** Kafka is popular message queue, can handle many messages simultaneously, suitable for real-time streaming.

### Q4: Can we run faster?

**A:** Yes, but won't be like real system. Accurate timing is important to test system correctly.

### Q5: How to know if system works correctly?

**A:** Check Grafana dashboard, see if data displays, check if timing is correct.

#!/usr/bin/env python3
"""
Real-time Kafka Producer for Hydraulic System Sensors
Simulates 17 sensors with accurate sampling rates
"""

import json
import time
import threading
from datetime import datetime
import os
import socket

# Monkey patch selectors to suppress "Invalid file descriptor" error (common in kafka-python)
import selectors
_orig_unregister = selectors.BaseSelector.unregister

def new_unregister(self, fileobj):
    try:
        return _orig_unregister(self, fileobj)
    except ValueError:
        pass
    except KeyError:
        pass

selectors.BaseSelector.unregister = new_unregister

# Import kafka AFTER patches are applied
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from pathlib import Path

# Kafka configuration
KAFKA_BROKER = "localhost:9092"

# Get project root directory (parent of src/)
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# Sensor configurations: (filename, sampling_rate_hz, num_samples_per_cycle)
SENSOR_CONFIGS = {
    # Pressure sensors (100Hz)
    "PS1": ("PS1.txt", 100, 6000),
    "PS2": ("PS2.txt", 100, 6000),
    "PS3": ("PS3.txt", 100, 6000),
    "PS4": ("PS4.txt", 100, 6000),
    "PS5": ("PS5.txt", 100, 6000),
    "PS6": ("PS6.txt", 100, 6000),
    # Motor power (100Hz)
    "EPS1": ("EPS1.txt", 100, 6000),
    # Volume flow (10Hz)
    "FS1": ("FS1.txt", 10, 600),
    "FS2": ("FS2.txt", 10, 600),
    # Temperature (1Hz)
    "TS1": ("TS1.txt", 1, 60),
    "TS2": ("TS2.txt", 1, 60),
    "TS3": ("TS3.txt", 1, 60),
    "TS4": ("TS4.txt", 1, 60),
    # Vibration (1Hz)
    "VS1": ("VS1.txt", 1, 60),
    # Virtual sensors (1Hz)
    "CE": ("CE.txt", 1, 60),
    "CP": ("CP.txt", 1, 60),
    "SE": ("SE.txt", 1, 60),
}


def load_cycle_data(filename, cycle_idx=0):
    filepath = DATA_DIR / filename
    with open(filepath, 'r') as f:
        lines = f.readlines()
        if cycle_idx >= len(lines):
            raise ValueError(f"Cycle {cycle_idx} not found in {filename}")
        
        values = lines[cycle_idx].strip().split('\t')
        return [float(v) for v in values]


class SensorProducer:
    """Producer for a single sensor"""
    
    def __init__(self, sensor_name, filename, sampling_rate_hz, num_samples, cycle_idx=0):
        self.sensor_name = sensor_name
        self.filename = filename
        self.sampling_rate_hz = sampling_rate_hz
        self.num_samples = num_samples
        self.cycle_idx = cycle_idx
        self.topic = f"hydraulic-{sensor_name}"
        
        # Calculate interval between samples (in seconds)
        self.interval = 1.0 / sampling_rate_hz
        
        # Load cycle data
        self.data = load_cycle_data(filename, cycle_idx)
        
        # Kafka producer
        self.producer = None
        
    def connect_kafka(self):
        """Connect to Kafka broker with retry"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BROKER,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks=1
                )
                print(f"[{self.sensor_name}] Connected to Kafka")
                return True
            except NoBrokersAvailable:
                if attempt < max_retries - 1:
                    print(f"[{self.sensor_name}] Kafka not ready, retry {attempt + 1}/{max_retries}...")
                    time.sleep(2)
                else:
                    print(f"[{self.sensor_name}] Failed to connect to Kafka")
                    return False
        return False
    
    def produce(self):
        """Produce sensor data with accurate timing"""
        if not self.connect_kafka():
            return
        
        print(f"[{self.sensor_name}] Starting producer: {self.sampling_rate_hz}Hz, "
              f"{len(self.data)} samples, interval={self.interval:.3f}s")
        
        start_time = time.time()
        
        for idx, value in enumerate(self.data):
            # Calculate expected time for this sample
            expected_time = start_time + (idx * self.interval)
            
            # Sleep until the expected time
            sleep_time = expected_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Create message
            message = {
                "sensor": self.sensor_name,
                "cycle": self.cycle_idx,
                "sample_idx": idx,
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "sampling_rate_hz": self.sampling_rate_hz
            }
            
            # Send to Kafka
            try:
                self.producer.send(self.topic, value=message)
                
                # Log every 100 samples for 100Hz, every 10 for 10Hz, all for 1Hz
                log_interval = 100 if self.sampling_rate_hz == 100 else (10 if self.sampling_rate_hz == 10 else 1)
                if (idx + 1) % log_interval == 0:
                    elapsed = time.time() - start_time
                    print(f"[{self.sensor_name}] Sent {idx + 1}/{len(self.data)} samples "
                          f"(elapsed: {elapsed:.2f}s, value: {value:.3f})")
            
            except Exception as e:
                print(f"[{self.sensor_name}] Error sending message: {e}")
        
        # Flush remaining messages
        self.producer.flush()
        total_time = time.time() - start_time
        
        print(f"[{self.sensor_name}] ✅ Completed! Sent {len(self.data)} samples in {total_time:.2f}s "
              f"(expected: 60s)")
        
        self.producer.close()


class HydraulicSystemProducer:
    """Main producer that manages all sensor producers"""
    
    def __init__(self, cycle_idx=0):
        self.cycle_idx = cycle_idx
        self.producers = []
        
        # Create producer instances
        for sensor_name, (filename, hz, num_samples) in SENSOR_CONFIGS.items():
            producer = SensorProducer(
                sensor_name=sensor_name,
                filename=filename,
                sampling_rate_hz=hz,
                num_samples=num_samples,
                cycle_idx=cycle_idx
            )
            self.producers.append(producer)
    
    def start(self):
        """Start all sensor producers in parallel"""
        print("=" * 80)
        print("🚀 Hydraulic System Real-time Data Producer")
        print("=" * 80)
        print(f"Kafka Broker: {KAFKA_BROKER}")
        print(f"Sensors: {len(SENSOR_CONFIGS)}")
        print(f"Cycle: {self.cycle_idx}")
        print("=" * 80)
        
        # Start all producers in separate threads
        threads = []
        for producer in self.producers:
            thread = threading.Thread(target=producer.produce, name=producer.sensor_name)
            thread.start()
            threads.append(thread)
            # Small delay to stagger thread starts
            time.sleep(0.01)
        
        print(f"\n🔥 Started {len(threads)} producer threads!\n")
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        print("\n" + "=" * 80)
        print(f"✅ All sensors completed producing data for cycle {self.cycle_idx} (60 seconds)")
        print("=" * 80)


def get_total_cycles(sensor_file="PS1.txt"):
    """Get total number of cycles available in data"""
    filepath = DATA_DIR / sensor_file
    with open(filepath, 'r') as f:
        return len(f.readlines())


def main():
    """Main function to start producer"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python producer.py <cycle_index>           # Run single cycle")
        print("  python producer.py <start> <end>           # Run cycles from start to end-1")
        print("  python producer.py --all                   # Run all cycles")
        print("  python producer.py --continuous [n]        # Run n cycles continuously (default 10)")
        print()
        print("Examples:")
        print("  python producer.py 0                       # Run cycle 0")
        print("  python producer.py 0 10                    # Run cycles 0-9")
        print("  python producer.py --all                   # Run all 2205 cycles")
        print("  python producer.py --continuous 5          # Run 5 random cycles")
        sys.exit(1)
    
    # Get total cycles available
    total_cycles = get_total_cycles()
    
    # Parse arguments
    if sys.argv[1] == "--all":
        # Run all cycles
        print(f"🔥 Running ALL {total_cycles} cycles...")
        print(f"⏱️  Estimated time: ~{total_cycles} minutes ({total_cycles/60:.1f} hours)")
        print()
        
        for cycle_idx in range(total_cycles):
            print(f"\n{'='*80}")
            print(f"📊 Cycle {cycle_idx + 1}/{total_cycles}")
            print(f"{'='*80}")
            
            producer = HydraulicSystemProducer(cycle_idx=cycle_idx)
            producer.start()
            
            if cycle_idx < total_cycles - 1:
                print(f"\n⏸️  Pausing 2 seconds before next cycle...")
                time.sleep(2)
    
    elif sys.argv[1] == "--continuous":
        # Run n cycles continuously
        n = 10  # default
        if len(sys.argv) > 2:
            try:
                n = int(sys.argv[2])
            except ValueError:
                print(f"❌ Invalid number: {sys.argv[2]}")
                sys.exit(1)
        
        print(f"🔄 Running {n} cycles continuously...")
        print(f"⏱️  Estimated time: ~{n} minutes")
        print()
        
        import random
        for i in range(n):
            cycle_idx = random.randint(0, total_cycles - 1)
            print(f"\n{'='*80}")
            print(f"📊 Iteration {i + 1}/{n} - Cycle {cycle_idx}")
            print(f"{'='*80}")
            
            producer = HydraulicSystemProducer(cycle_idx=cycle_idx)
            producer.start()
            
            if i < n - 1:
                print(f"\n⏸️  Pausing 2 seconds before next cycle...")
                time.sleep(2)
    
    elif len(sys.argv) == 3:
        # Run range of cycles
        try:
            start = int(sys.argv[1])
            end = int(sys.argv[2])
            
            if start < 0 or end > total_cycles or start >= end:
                print(f"❌ Invalid range: {start}-{end}")
                print(f"   Valid range: 0-{total_cycles}")
                sys.exit(1)
            
            num_cycles = end - start
            print(f"📊 Running cycles {start} to {end-1} ({num_cycles} cycles)")
            print(f"⏱️  Estimated time: ~{num_cycles} minutes")
            print()
            
            for cycle_idx in range(start, end):
                print(f"\n{'='*80}")
                print(f"📊 Cycle {cycle_idx} ({cycle_idx - start + 1}/{num_cycles})")
                print(f"{'='*80}")
                
                producer = HydraulicSystemProducer(cycle_idx=cycle_idx)
                producer.start()
                
                if cycle_idx < end - 1:
                    print(f"\n⏸️  Pausing 2 seconds before next cycle...")
                    time.sleep(2)
        
        except ValueError:
            print(f"❌ Invalid arguments: {sys.argv[1]} {sys.argv[2]}")
            print("   Both must be integers")
            sys.exit(1)
    
    else:
        # Run single cycle
        try:
            cycle_idx = int(sys.argv[1])
            
            if cycle_idx < 0 or cycle_idx >= total_cycles:
                print(f"❌ Invalid cycle index: {cycle_idx}")
                print(f"   Valid range: 0-{total_cycles - 1}")
                sys.exit(1)
            
            producer = HydraulicSystemProducer(cycle_idx=cycle_idx)
            producer.start()
        
        except ValueError:
            print(f"❌ Invalid cycle index: {sys.argv[1]}")
            print("   Must be an integer")
            sys.exit(1)


if __name__ == "__main__":
    main()


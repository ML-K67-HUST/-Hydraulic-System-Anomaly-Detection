
import time
import json
import socket
import os
import sys

# --- DNS Patch for "kafka:9092" ---
# Broker advertises "kafka", so we must resolve that to 127.0.0.1
_orig_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'kafka':
        print(f"🔄 Redirecting 'kafka' to '127.0.0.1'...")
        host = '127.0.0.1'
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = new_getaddrinfo

# --- Selectors Patch for Python compatibility ---
import selectors
if hasattr(selectors, 'KqueueSelector'):
    _orig_unregister = selectors.KqueueSelector.unregister
    def new_unregister(self, fileobj):
        try:
            return _orig_unregister(self, fileobj)
        except (ValueError, OSError):
            pass
    selectors.KqueueSelector.unregister = new_unregister

from kafka import KafkaProducer

def main():
    print("🚀 Starting Simple Producer...")
    
    # 1. Connect
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version_auto_timeout_ms=5000,
            request_timeout_ms=5000
        )
        print("✅ Connected to Kafka!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # 2. Read Data
    topic = "hydraulic-PS1"
    filepath = "../data/PS1.txt"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        # Try absolute path based on known location
        filepath = "/Users/khangtuan/Documents/courses/big_data/-Hydraulic-System-Anomaly-Detection/data/PS1.txt"
    
    print(f"📖 Reading from {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Cannot read file: {e}")
        return

    print(f"📤 Sending {len(lines)} cycles to topic '{topic}'...")

    # 3. Send Loop
    for i, line in enumerate(lines):
        # Taking just the first few values of the cycle to keep it simple
        values = line.strip().split('\t')
        
        # Send one message per cycle for testing, or multiple if needed. 
        # User said "producer lấy dữ liệu từ file txt rồi bắn vào cùng topic"
        # Let's send the whole array as one message, OR one message per sample.
        # Original producer sent samples individually. Let's do samples individually for the first cycle only to test flow.
        
        # Simulating first cycle only for simplicity as requested
        print(f"🔄 Sending Cycle {i} data...")
        
        for idx, val in enumerate(values):
            msg = {
                "sensor": "PS1",
                "val": float(val),
                "cycle": i,
                "idx": idx,
                "ts": time.time()
            }
            producer.send(topic, value=msg)
            
            if idx % 100 == 0:
                print(f"   Sent sample {idx}/{len(values)}")
                producer.flush() # Force send immediately for debugging
                
        time.sleep(1) # Slow down to see it happening
        if i >= 5: # Just do 5 cycles for test
            break
            
    producer.flush()
    producer.close()
    print("✅ Done!")

if __name__ == "__main__":
    main()

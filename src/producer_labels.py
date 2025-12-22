import time
import json
import argparse
from kafka import KafkaProducer

# Configuration
KAFKA_BROKER = 'localhost:9092'
TOPIC_LABELS = 'hydraulic-labels'
DATA_FILE = 'data/profile.txt'

def main():
    parser = argparse.ArgumentParser(description="Hydraulic System Label Producer")
    parser.add_argument('--delay', type=float, default=0.001, help="Delay between sending cycles (seconds)")
    args = parser.parse_args()

    # Initialize Kafka Producer
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    print(f"✅ Connected to Kafka at {KAFKA_BROKER}")
    print(f"📡 Sending labels to topic: {TOPIC_LABELS}")

    try:
        with open(DATA_FILE, 'r') as f:
            lines = f.readlines()

        total_cycles = len(lines)
        print(f"📖 Found {total_cycles} cycles in {DATA_FILE}")

        for i, line in enumerate(lines):
            cycle_id = i + 1
            parts = line.strip().split()
            
            # Profile.txt columns:
            # 1: Cooler condition (3, 20, 100)
            # 2: Valve condition (100, 90, 80, 73)
            # 3: Internal pump leakage (0, 1, 2)
            # 4: Hydraulic accumulator (130, 115, 100, 90)
            # 5: stable flag (0, 1)

            if len(parts) != 5:
                print(f"⚠️ Skipping malformed line {i+1}: {line.strip()}")
                continue

            payload = {
                'cycle': cycle_id,
                'label_cooler': int(float(parts[0])),
                'label_valve': int(float(parts[1])),
                'label_pump': int(float(parts[2])),
                'label_accumulator': int(float(parts[3])),
                'label_stable': int(float(parts[4])),
                'timestamp': time.time()
            }

            producer.send(TOPIC_LABELS, value=payload)
            
            if cycle_id % 100 == 0:
                print(f"📤 Sent cycle {cycle_id}/{total_cycles}")
            
            time.sleep(args.delay)

        producer.flush()
        print("✅ Finished sending all labels.")

    except FileNotFoundError:
        print(f"❌ Error: File {DATA_FILE} not found.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        producer.close()

if __name__ == "__main__":
    main()

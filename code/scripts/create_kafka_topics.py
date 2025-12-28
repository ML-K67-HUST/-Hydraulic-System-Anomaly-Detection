#!/usr/bin/env python3
"""
Create Kafka topics for 17 hydraulic sensors
"""

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import time
import socket

# Kafka broker
KAFKA_BROKER = "localhost:9092"

# 17 sensors với sampling rates
SENSORS = {
    # Pressure sensors (100Hz)
    "PS1": 100, "PS2": 100, "PS3": 100, "PS4": 100, "PS5": 100, "PS6": 100,
    # Motor power (100Hz)
    "EPS1": 100,
    # Volume flow (10Hz)
    "FS1": 10, "FS2": 10,
    # Temperature (1Hz)
    "TS1": 1, "TS2": 1, "TS3": 1, "TS4": 1,
    # Vibration (1Hz)
    "VS1": 1,
    # Virtual sensors (1Hz)
    "CE": 1, "CP": 1, "SE": 1
}

def create_topics():
    """Create Kafka topics for all sensors"""
    print("Connecting to Kafka broker...")
    
    # Retry logic for Kafka connection
    max_retries = 5
    for attempt in range(max_retries):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_BROKER,
                client_id='hydraulic-topic-creator'
            )
            print(f"Connected to Kafka at {KAFKA_BROKER}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed, retrying in 2s...")
                time.sleep(2)
            else:
                print(f"Failed to connect to Kafka: {e}")
                return
    
    # Create topics
    topics = []
    for sensor, hz in SENSORS.items():
        topic_name = f"hydraulic-{sensor}"
        topics.append(NewTopic(
            name=topic_name,
            num_partitions=1,
            replication_factor=1
        ))
    
    try:
        admin_client.create_topics(new_topics=topics, validate_only=False)
        print(f"\n✅ Successfully created {len(topics)} topics:")
        for sensor, hz in SENSORS.items():
            print(f"   - hydraulic-{sensor} (sampling rate: {hz} Hz)")
    except TopicAlreadyExistsError:
        print("\n⚠️  Topics already exist, skipping creation")
    except Exception as e:
        print(f"\n❌ Error creating topics: {e}")
    
    # List all topics
    print("\n📋 All Kafka topics:")
    try:
        all_topics = admin_client.list_topics()
        hydraulic_topics = [t for t in all_topics if t.startswith('hydraulic-')]
        for topic in sorted(hydraulic_topics):
            print(f"   - {topic}")
    except Exception as e:
        print(f"Error listing topics: {e}")
    
    admin_client.close()

if __name__ == "__main__":
    create_topics()


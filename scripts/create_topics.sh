#!/bin/bash

# Kafka broker
KAFKA_BROKER="localhost:29092"

# 17 sensors
SENSORS=(
  "PS1" "PS2" "PS3" "PS4" "PS5" "PS6"  # Pressure sensors (100Hz)
  "EPS1"                                 # Motor power (100Hz)
  "FS1" "FS2"                           # Volume flow (10Hz)
  "TS1" "TS2" "TS3" "TS4"               # Temperature (1Hz)
  "VS1"                                  # Vibration (1Hz)
  "CE" "CP" "SE"                        # Virtual sensors (1Hz)
)

echo "Creating Kafka topics for 17 sensors..."

# Exec into Kafka container to create topics
for sensor in "${SENSORS[@]}"; do
  echo "Creating topic: hydraulic-$sensor"
  docker exec hydraulic-system-anomaly-detection-kafka-1 \
    kafka-topics.sh \
    --create \
    --if-not-exists \
    --topic "hydraulic-$sensor" \
    --partitions 1 \
    --replication-factor 1 \
    --bootstrap-server localhost:9092
done

echo "All topics created successfully!"

# List all topics
echo -e "\nListing all topics:"
docker exec hydraulic-system-anomaly-detection-kafka-1 \
  kafka-topics.sh \
  --list \
  --bootstrap-server localhost:9092 | grep hydraulic


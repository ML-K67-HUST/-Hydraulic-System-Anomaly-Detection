
import json
import time
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import sys

# Monkey patch selectors to suppress "Invalid file descriptor" error (common in kafka-python)
import selectors

# Patch all available selector types on this platform
for selector_name in ['SelectSelector', 'PollSelector', 'EpollSelector', 'KqueueSelector', 'DevpollSelector']:
    selector_class = getattr(selectors, selector_name, None)
    if selector_class is not None:
        original_unregister = selector_class.unregister
        
        def make_patched_unregister(orig_method):
            def patched_unregister(self, fileobj):
                try:
                    return orig_method(self, fileobj)
                except (ValueError, KeyError, OSError):
                    pass
            return patched_unregister
        
        selector_class.unregister = make_patched_unregister(original_unregister)


# Import kafka AFTER patches are applied
from kafka import KafkaConsumer


import os

# Kafka configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
CONSUMER_GROUP_PREFIX = "hydraulic"
PROMETHEUS_JOB_NAME = "hydraulic_spark"  # Unique job for this consumer

# Analytics topic Only
ANALYTICS_TOPIC = "hydraulic-analytics"


class BaseConsumer(ABC):
    
    def __init__(self, group_id_suffix: str):
        self.group_id = f"{CONSUMER_GROUP_PREFIX}-{group_id_suffix}"
        self.consumer = None
        self.message_count = 0
        
    def create_consumer(self):
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    ANALYTICS_TOPIC,
                    bootstrap_servers=[KAFKA_BROKER],
                    group_id=self.group_id,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    # consumer_timeout_ms=float('inf'),
                    request_timeout_ms=30000,
                    api_version_auto_timeout_ms=5000
                )
                print(f"✅ Connected to Kafka at {KAFKA_BROKER}", flush=True)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Kafka not ready (attempt {attempt + 1}/{max_retries}): {e}", flush=True)
                    print(f"   Retrying in {retry_delay} seconds...", flush=True)
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Failed to connect to Kafka after {max_retries} attempts", flush=True)
                    raise
    
    @abstractmethod
    def process_message(self, message):
        """Process a single message - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def on_start(self):
        """Called before consuming starts"""
        pass
    
    @abstractmethod
    def on_stop(self):
        """Called when consuming stops"""
        pass
    
    def consume(self):
        """Main consumption loop"""
        self.create_consumer()
        self.on_start()
        
        print("\n📊 Consuming ANALYTICS messages... (Ctrl+C to stop)\n")
        
        try:
            for message in self.consumer:
                try:
                    self.process_message(message)
                    self.message_count += 1
                    
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    continue
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping consumer...")
        
        finally:
            self.on_stop()
            if self.consumer:
                self.consumer.close()
            
            print("\n" + "=" * 80)
            print(f"✅ Consumer stopped. Total messages: {self.message_count:,}")
            print("=" * 80)


class PrometheusConsumer(BaseConsumer):
    def __init__(self, pushgateway_url: str = None):
        super().__init__("prometheus-analytics")
        self.pushgateway_url = pushgateway_url or os.getenv("PUSHGATEWAY_URL", "localhost:9091")
        self.push_interval = 2  # seconds
        self.last_push_time = None
        
        from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, Counter
        self.push_to_gateway = push_to_gateway
        
        self.registry = CollectorRegistry()
        
        # Aggregated metrics (from Spark) only
        self.sensor_avg = Gauge(
            'hydraulic_sensor_avg_1m', '1-minute moving average', ['sensor'], registry=self.registry
        )
        self.sensor_max = Gauge(
            'hydraulic_sensor_max_1m', '1-minute max value', ['sensor'], registry=self.registry
        )
        self.sensor_min = Gauge(
            'hydraulic_sensor_min_1m', '1-minute min value', ['sensor'], registry=self.registry
        )
        self.sensor_stddev = Gauge(
            'hydraulic_sensor_stddev_1m', '1-minute standard deviation', ['sensor'], registry=self.registry
        )
        self.sensor_range = Gauge(
            'hydraulic_sensor_range_1m', '1-minute range (max-min)', ['sensor'], registry=self.registry
        )
        
        # Anomaly Detection Metrics
        self.anomaly_status = Gauge(
            'hydraulic_anomaly_status', 'Anomaly Detected (1=Yes, 0=No)', ['sensor', 'type'], registry=self.registry
        )
        self.anomaly_total = Counter(
            'hydraulic_anomaly_total',
            'Total count of detected anomalies',
            ['sensor', 'type']
        )
        
        # New Metric: System Health Score (Per Sensor)
        self.system_health_score = Gauge(
            'hydraulic_sensor_health_score',
            'Health Score of the sensor (0-100)',
            ['sensor'],
            registry=self.registry
        )
        self.anomaly_counters = {} # Local counter for total gauge

        self.total_messages = Gauge(
            'hydraulic_analytics_messages_total',
            'Total analytics messages consumed from Kafka',
            registry=self.registry
        )
        
        self.last_update_time = Gauge(
            'hydraulic_analytics_last_update_timestamp',
            'Unix timestamp of last update',
            registry=self.registry
        )
        
    
    def on_start(self):
        print("=" * 80)
        print("🚀 Prometheus Consumer (SPARK ANALYTICS)")
        print("=" * 80)
        print(f"Kafka Broker: {KAFKA_BROKER}")
        print(f"Pushgateway: {self.pushgateway_url}")
        print(f"Job Name: {PROMETHEUS_JOB_NAME}")
        print(f"Topics: {ANALYTICS_TOPIC}")
        print("=" * 80)
        self.last_push_time = time.time()
    
    def push_metrics(self):
        try:
            self.push_to_gateway(
                self.pushgateway_url,
                job=PROMETHEUS_JOB_NAME,
                registry=self.registry
            )
        except Exception as e:
            print(f"⚠️  Failed to push metrics: {e}")
    
    def process_message(self, message):
        data = message.value
        sensor = data.get('sensor')
        
        # Handle Aggregated Data (from Spark)
        if 'avg_value' in data:
            self.sensor_avg.labels(sensor=sensor).set(data['avg_value'])
            self.sensor_max.labels(sensor=sensor).set(data['max_value'])
            self.sensor_min.labels(sensor=sensor).set(data['min_value'])
            
            # New Metrics (StdDev, Range)
            if 'stddev_value' in data:
                 self.sensor_stddev.labels(sensor=sensor).set(data['stddev_value'])
            if 'range_value' in data:
                 self.sensor_range.labels(sensor=sensor).set(data['range_value'])
            
            print(f"📊 [Spark] {sensor} Aggregation: Avg={data['avg_value']:.2f}, Range={data.get('range_value', 0):.2f}", flush=True)

            # --- ANOMALY DETECTION LOGIC ---
            self.check_anomalies(sensor, data)
            
            # Update generic metrics
            self.total_messages.set(self.message_count + 1)
            self.last_update_time.set(time.time())

    def check_anomalies(self, sensor, data):
        """Check for anomalies based on thresholds and rules"""
        avg_val = data.get('avg_value', 0)
        max_val = data.get('max_value', 0)
        range_val = data.get('range_value', 0)
        
        anomalies = []
        
        # Rule 1: High Pressure (PS1 > 180 bar) - Use max to catch spikes (Normal is ~160)
        if sensor == 'PS1' and max_val > 180:
            anomalies.append('high_pressure')
        
        # Rule 2: High Temperature (TS1 > 45 C) (Normal is ~45)
        if sensor == 'TS1' and max_val > 45:
            anomalies.append('high_temperature')

        # Rule 3: Pressure Spike (Range > 50 bar) - General for Pressure sensors
        if sensor.startswith('PS') and range_val > 50:
            anomalies.append('pressure_spike')
            
        # Reset Status first (Aggressive reset for realtime dashboarding)
        # Only reset RELEVANT anomaly types to avoid polluting Prometheus series
        
        relevant_anomalies = []
        if sensor.startswith('PS'):
             relevant_anomalies = ['high_pressure', 'pressure_spike']
        elif sensor.startswith('TS'):
             relevant_anomalies = ['high_temperature']
        
        for anomaly_type in relevant_anomalies:
             self.anomaly_status.labels(sensor=sensor, type=anomaly_type).set(0)

        # Set Anomaly Status if detected
        active_anomaly_count = 0
        for anomaly_type in anomalies:
            print(f"🚨 ANOMALY DETECTED [{sensor}]: {anomaly_type} (Val: {max_val:.2f})", flush=True)
            self.anomaly_status.labels(sensor=sensor, type=anomaly_type).set(1)
            active_anomaly_count += 1
            
            # Increment total counter
            self.anomaly_total.labels(sensor=sensor, type=anomaly_type).inc()

        # Update System Health Score
        # Logic: Base 100.
        # - High Pressure/Temp: -20 points (Critical)
        # - Spike: -10 points (Warning)
        # We need to track GLOBAL health, so we might need a separate accumulator or just approximate it by sensor impact.
        # For simplicity in this consumer: We emit a per-sensor health impact, and Aggregation happens in Grafana/Prometheus?
        # NO, simpler: Just emit a 'hydraulic_sensor_health' metric (0-100) for this sensor.
        
        sensor_health = 100
        for anomaly_type in anomalies:
             if 'spike' in anomaly_type:
                  sensor_health -= 10
             else:
                  sensor_health -= 20 # Critical
        
        sensor_health = max(0, sensor_health)
        self.system_health_score.labels(sensor=sensor).set(sensor_health)
        
        current_time = time.time()
        if current_time - self.last_push_time >= self.push_interval:
            self.push_metrics()
            self.last_push_time = current_time
            if (self.message_count + 1) % 10 == 0: # More frequent logging for analytics due to lower volume
                print(f"✅ Pushed metrics to Prometheus ({self.message_count + 1:,} total)")
    
    def on_stop(self):
        self.push_metrics()
        print("✅ Final metrics pushed to Prometheus")


def main():
    consumer = PrometheusConsumer()
    consumer.consume()


if __name__ == "__main__":
    main()


import json
import time
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import sys  # Added missing import

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


# Kafka configuration
KAFKA_BROKER = "localhost:9092"
CONSUMER_GROUP_PREFIX = "hydraulic"
PROMETHEUS_JOB_NAME = "hydraulic_raw"  # Unique job for this consumer

# Raw Sensor topics Only
SENSOR_TOPICS = [
    "hydraulic-PS1", "hydraulic-PS2", "hydraulic-PS3", 
    "hydraulic-PS4", "hydraulic-PS5", "hydraulic-PS6",
    "hydraulic-EPS1",
    "hydraulic-FS1", "hydraulic-FS2",
    "hydraulic-TS1", "hydraulic-TS2", "hydraulic-TS3", "hydraulic-TS4",
    "hydraulic-CE", "hydraulic-CP", "hydraulic-SE", "hydraulic-VS1"
]


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
                    *SENSOR_TOPICS,
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
                print(f"✅ Connected to Kafka at {KAFKA_BROKER}")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Kafka not ready (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Failed to connect to Kafka after {max_retries} attempts")
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
        
        print("\n📊 Consuming messages... (Ctrl+C to stop)\n")
        
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
    def __init__(self, pushgateway_url: str = "localhost:9091"):
        super().__init__("prometheus-raw")
        self.pushgateway_url = pushgateway_url
        self.push_interval = 2  # seconds
        self.last_push_time = None
        
        from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
        self.push_to_gateway = push_to_gateway
        
        self.registry = CollectorRegistry()
        self.sensor_values = {}
        self.sensor_sample_counts = {}
        self.sample_counts = {}
        
        for topic in SENSOR_TOPICS:
            sensor_name = topic.replace("hydraulic-", "")
            
            self.sensor_values[sensor_name] = Gauge(
                f'hydraulic_raw_{sensor_name.lower()}', # Renamed to force fresh series
                f'{sensor_name} sensor reading',
                ['sensor'], 
                registry=self.registry
            )
            
            self.sensor_sample_counts[sensor_name] = Gauge(
                f'hydraulic_{sensor_name.lower()}_samples_total',
                f'Total samples received from {sensor_name}',
                ['sensor'],
                registry=self.registry
            )
            
            self.sample_counts[sensor_name] = 0
        
        Gauge = Gauge  
        self.total_messages = Gauge(
            'hydraulic_messages_total',
            'Total messages consumed from Kafka',
            registry=self.registry
        )
        
        self.last_update_time = Gauge(
            'hydraulic_last_update_timestamp',
            'Unix timestamp of last update',
            registry=self.registry
        )
        
    
    def on_start(self):
        print("=" * 80)
        print("🚀 Prometheus Consumer (RAW DATA)")
        print("=" * 80)
        print(f"Kafka Broker: {KAFKA_BROKER}")
        print(f"Pushgateway: {self.pushgateway_url}")
        print(f"Job Name: {PROMETHEUS_JOB_NAME}")
        print(f"Topics: {len(SENSOR_TOPICS)} sensors")
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

        # Handle Raw Sensor Data ONLY
        if 'value' in data:
            value = data['value']
            cycle = data.get('cycle', 0)
            sample_idx = data.get('sample_idx', 0)
            
            if sensor in self.sensor_values:
                # Do NOT include 'cycle' as a label to avoid high cardinality (label explosion)
                self.sensor_values[sensor].labels(
                    sensor=sensor
                ).set(value)
            
            self.sample_counts[sensor] += 1

            if sensor in self.sensor_sample_counts:
                self.sensor_sample_counts[sensor].labels(
                    sensor=sensor
                ).set(self.sample_counts[sensor])
            
            self.total_messages.set(self.message_count + 1)
            self.last_update_time.set(time.time())
            
            if (self.message_count + 1) % 100 == 0:
                print(f"📈 [{sensor}] Sample {sample_idx}: {value:.3f} "
                      f"(Total: {self.message_count + 1:,})")
        
        current_time = time.time()
        if current_time - self.last_push_time >= self.push_interval:
            self.push_metrics()
            self.last_push_time = current_time
            if (self.message_count + 1) % 500 == 0:
                print(f"✅ Pushed metrics to Prometheus ({self.message_count + 1:,} total)")
    
    def on_stop(self):
        self.push_metrics()
        print("✅ Final metrics pushed to Prometheus")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "mongodb":
         print("❌ MongoDB consumer not supported in consumer_raw.py. Use consumer.py for Mongo.")
         sys.exit(1)
         
    consumer = PrometheusConsumer()
    consumer.consume()


if __name__ == "__main__":
    main()

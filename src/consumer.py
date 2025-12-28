
import json
import time
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import socket
import os

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
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
CONSUMER_GROUP_PREFIX = "hydraulic"

# Sensor topics
SENSOR_TOPICS = [
    "hydraulic-PS1", "hydraulic-PS2", "hydraulic-PS3", 
    "hydraulic-PS4", "hydraulic-PS5", "hydraulic-PS6",
    "hydraulic-EPS1",
    "hydraulic-FS1", "hydraulic-FS2",
    "hydraulic-TS1", "hydraulic-TS2", "hydraulic-TS3", "hydraulic-TS4",
    "hydraulic-CE", "hydraulic-CP", "hydraulic-SE", "hydraulic-VS1",
    "hydraulic-analytics"  # Processed data from Spark
]


class BaseConsumer(ABC):
    
    def __init__(self, group_id_suffix: str):
        self.group_id = f"{CONSUMER_GROUP_PREFIX}-{group_id_suffix}"
        self.consumer = None
        self.message_count = 0
        
    def create_consumer(self):
        max_retries = 30
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
    def __init__(self, pushgateway_url: str = None):
        super().__init__("prometheus-group-v2")
        self.pushgateway_url = pushgateway_url or os.getenv("PUSHGATEWAY_URL", "localhost:9091")
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
                f'hydraulic_{sensor_name.lower()}_value_clean',
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
        
        # Aggregated metrics (from Spark)
        self.sensor_avg = Gauge(
            'hydraulic_sensor_avg_1m', '1-minute moving average', ['sensor'], registry=self.registry
        )
        self.sensor_max = Gauge(
            'hydraulic_sensor_max_1m', '1-minute max value', ['sensor'], registry=self.registry
        )
        self.sensor_min = Gauge(
            'hydraulic_sensor_min_1m', '1-minute min value', ['sensor'], registry=self.registry
        )
    
    def on_start(self):
        print("=" * 80)
        print("🚀 Prometheus Consumer")
        print("=" * 80)
        print(f"Kafka Broker: {KAFKA_BROKER}")
        print(f"Pushgateway: {self.pushgateway_url}")
        print(f"Topics: {len(SENSOR_TOPICS)} sensors")
        print("=" * 80)
        self.last_push_time = time.time()
    
    def push_metrics(self):
        try:
            self.push_to_gateway(
                self.pushgateway_url,
                job='hydraulic_system',
                registry=self.registry
            )
        except Exception as e:
            print(f"⚠️  Failed to push metrics: {e}")
    
    def process_message(self, message):
        data = message.value
        sensor = data.get('sensor')
        
        # 1. Handle Aggregated Data (from Spark)
        if 'avg_value' in data:
            self.sensor_avg.labels(sensor=sensor).set(data['avg_value'])
            self.sensor_max.labels(sensor=sensor).set(data['max_value'])
            self.sensor_min.labels(sensor=sensor).set(data['min_value'])
            print(f"📊 [Spark] {sensor} Aggregation: Avg={data['avg_value']:.2f}")
            
            # Update generic metrics
            self.total_messages.set(self.message_count + 1)
            self.last_update_time.set(time.time())
            return

        # 2. Handle Raw Sensor Data (from Producer)
        if 'value' in data:
            value = data['value']
            cycle = data.get('cycle', 0)
            sample_idx = data.get('sample_idx', 0)
            
            if sensor in self.sensor_values:
                self.sensor_values[sensor].labels(
                    sensor=sensor
                ).set(value)
            
            self.sample_counts[sensor] += 1
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


class MongoDBConsumer(BaseConsumer):
    
    def __init__(self, mongo_uri: str = None,
                 db_name: str = "hydraulic_system",
                 collection_name: str = "sensor_readings",
                 analytics_collection_name: str = "sensor_analytics"):
        super().__init__("mongodb-group")
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = db_name
        self.collection_name = collection_name
        self.analytics_collection_name = analytics_collection_name
        
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.analytics_collection = None
        
        self.batch_raw = []
        self.batch_analytics = []
        self.batch_size = 100
        self.batch_interval = 2  # seconds
        self.last_batch_time = None
        self.lock = threading.Lock()
    
    def connect_mongodb(self):
        try:
            from pymongo import MongoClient
            
            self.mongo_client = MongoClient(self.mongo_uri)
            self.db = self.mongo_client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.analytics_collection = self.db[self.analytics_collection_name]
            
            self.mongo_client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {self.mongo_uri}/{self.db_name}")
            
            self.collection.create_index("sensor")
            self.collection.create_index("timestamp")
            
            self.analytics_collection.create_index("sensor")
            print("✅ Created indexes for both collections")
            
            return True
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
    
    def on_start(self):
        """Initialize MongoDB connection"""
        print("=" * 80)
        print("🚀 MongoDB Consumer")
        print("=" * 80)
        print(f"Kafka Broker: {KAFKA_BROKER}")
        print(f"MongoDB: {self.mongo_uri}/{self.db_name}")
        print(f"Topics: {len(SENSOR_TOPICS)} sensors")
        print("=" * 80)
        
        if not self.connect_mongodb():
            raise Exception("Failed to connect to MongoDB")
        
        self.last_batch_time = time.time()
    
    def write_batch(self):
        """Write batch to MongoDB"""
        if not self.batch:
            return
        
        try:
            with self.lock:
                raw_to_write = self.batch_raw.copy()
                analytics_to_write = self.batch_analytics.copy()
                self.batch_raw = []
                self.batch_analytics = []
            
            if raw_to_write:
                self.collection.insert_many(raw_to_write)
            
            if analytics_to_write:
                self.analytics_collection.insert_many(analytics_to_write)
                print(f"✅ Wrote {len(raw_to_write)} Raw + {len(analytics_to_write)} Analytics msg")
            elif raw_to_write:
                 print(f"✅ Wrote {len(raw_to_write)} Raw records")
        
        except Exception as e:
            print(f"❌ Error writing to MongoDB: {e}")
    
    def process_message(self, message):
        data = message.value
        
        data['kafka_timestamp'] = datetime.fromtimestamp(
            message.timestamp / 1000
        ).isoformat()
        data['kafka_partition'] = message.partition
        data['kafka_offset'] = message.offset
        
        data['kafka_offset'] = message.offset
        
        with self.lock:
            if 'avg_value' in data:
                self.batch_analytics.append(data)
            else:
                self.batch_raw.append(data)
        
        if (self.message_count + 1) % 100 == 0:
            sensor = data.get('sensor', 'unknown')
            value = data.get('value', 0)
            sample_idx = data.get('sample_idx', 0)
            print(f"📊 [{sensor}] Sample {sample_idx}: {value:.3f} "
                  f"(Total received: {self.message_count + 1})")
        
        current_time = time.time()
        if current_time - self.last_batch_time >= self.batch_interval:
            self.write_batch()
            self.last_batch_time = current_time
    
    def on_stop(self):
        self.write_batch()
        
        if self.mongo_client:
            self.mongo_client.close()
            print("✅ MongoDB connection closed")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python consumer.py [prometheus|mongodb]")
        print()
        print("Examples:")
        print("  python consumer.py prometheus")
        print("  python consumer.py mongodb")
        sys.exit(1)
    
    consumer_type = sys.argv[1].lower()
    
    if consumer_type == "prometheus":
        consumer = PrometheusConsumer()
    elif consumer_type == "mongodb":
        consumer = MongoDBConsumer()
    else:
        print(f"❌ Unknown consumer type: {consumer_type}")
        print("Available types: prometheus, mongodb")
        sys.exit(1)
    
    consumer.consume()


if __name__ == "__main__":
    main()


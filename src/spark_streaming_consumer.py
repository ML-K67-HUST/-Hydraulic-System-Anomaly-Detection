#!/usr/bin/env python3
"""
Spark Structured Streaming Consumer for Hydraulic System
Consumes from Kafka topics and performs real-time aggregations
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, avg, max, min, count,
    sum as spark_sum, struct, to_timestamp, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
)
import sys
import os

# Kafka configuration
KAFKA_BROKER = "localhost:29092"
KAFKA_TOPICS = ",".join([
    "hydraulic-PS1", "hydraulic-PS2", "hydraulic-PS3",
    "hydraulic-PS4", "hydraulic-PS5", "hydraulic-PS6",
    "hydraulic-EPS1",
    "hydraulic-FS1", "hydraulic-FS2",
    "hydraulic-TS1", "hydraulic-TS2", "hydraulic-TS3", "hydraulic-TS4",
    "hydraulic-CE", "hydraulic-CP", "hydraulic-SE", "hydraulic-VS1"
])

# Checkpoint location for Spark Streaming
CHECKPOINT_DIR = "/tmp/spark-checkpoints/hydraulic-streaming"

# Schema for Kafka messages
MESSAGE_SCHEMA = StructType([
    StructField("sensor", StringType(), True),
    StructField("cycle", IntegerType(), True),
    StructField("sample_idx", IntegerType(), True),
    StructField("value", DoubleType(), True),
    StructField("timestamp", StringType(), True),
    StructField("sampling_rate_hz", IntegerType(), True)
])


def create_spark_session():
    """Create Spark session with Kafka support"""
    spark = SparkSession.builder \
        .appName("HydraulicSystemStreaming") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


def read_from_kafka(spark):
    """Read streaming data from Kafka"""
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", KAFKA_TOPICS) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse JSON messages
    df_parsed = df.select(
        col("timestamp").alias("kafka_timestamp"),
        from_json(col("value").cast("string"), MESSAGE_SCHEMA).alias("data")
    ).select(
        col("kafka_timestamp"),
        col("data.sensor"),
        col("data.cycle"),
        col("data.sample_idx"),
        col("data.value"),
        to_timestamp(col("data.timestamp")).alias("event_timestamp"),
        col("data.sampling_rate_hz")
    )
    
    return df_parsed


def process_stream(df):
    """Process streaming data with aggregations"""
    
    # Window aggregations (1 minute windows)
    windowed = df \
        .withWatermark("event_timestamp", "10 seconds") \
        .groupBy(
            window("event_timestamp", "1 minute"),
            "sensor"
        ) \
        .agg(
            count("*").alias("message_count"),
            avg("value").alias("avg_value"),
            max("value").alias("max_value"),
            min("value").alias("min_value"),
            spark_sum("value").alias("sum_value")
        )
    
    return windowed


def write_to_console(df):
    """Write results to console (for debugging)"""
    query = df \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    return query


def write_to_memory(df, table_name="hydraulic_aggregations"):
    """Write results to in-memory table (for querying)"""
    query = df \
        .writeStream \
        .outputMode("update") \
        .format("memory") \
        .queryName(table_name) \
        .trigger(processingTime="10 seconds") \
        .start()
    
    return query


def main():
    """Main function"""
    print("=" * 50)
    print("🚀 Spark Structured Streaming Consumer")
    print("=" * 50)
    print(f"Kafka Broker: {KAFKA_BROKER}")
    print(f"Topics: {KAFKA_TOPICS}")
    print(f"Checkpoint: {CHECKPOINT_DIR}")
    print("=" * 50)
    print()
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read from Kafka
        print("📥 Reading from Kafka...")
        df_stream = read_from_kafka(spark)
        
        # Process stream
        print("⚙️  Processing stream...")
        df_processed = process_stream(df_stream)
        
        # Write to console (for monitoring)
        print("📊 Starting streaming query...")
        query = write_to_console(df_processed)
        
        # Also write to memory for querying
        query_memory = write_to_memory(df_processed)
        
        print("✅ Streaming started! Waiting for data...")
        print("   Press Ctrl+C to stop")
        print()
        
        # Wait for termination
        query.awaitTermination()
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping streaming...")
        query.stop()
        query_memory.stop()
        spark.stop()
        print("✅ Stopped successfully")
    except Exception as e:
        print(f"❌ Error: {e}")
        spark.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()


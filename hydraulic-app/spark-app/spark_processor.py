
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Configuration from Environment Variables (with defaults for Kubernetes)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-service.kafka.svc.cluster.local:9092")
HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "hdfs://hdfs-namenode-0.hdfs-namenode.hdfs.svc.cluster.local:9000")
CHECKPOINT_DIR = os.getenv("CHECKPOINT_DIR", "/user/spark/checkpoints")
KAFKA_STARTING_OFFSETS = os.getenv("KAFKA_STARTING_OFFSETS", "latest")

def main():
    spark = SparkSession.builder \
        .appName("HydraulicSystem-Streaming-Analytics") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    
    print(f"🚀 Starting Spark Analytics...")
    print(f"🔗 Kafka Broker: {KAFKA_BROKER}")
    print(f"💾 HDFS Namenode: {HDFS_NAMENODE}")
    print(f"🏁 Starting Offsets: {KAFKA_STARTING_OFFSETS}")

    # --- SCHEMAS ---
    
    # Schema for Labels (profile.txt)
    schema_labels = StructType([
        StructField("cycle", IntegerType()),
        StructField("label_cooler", IntegerType()),
        StructField("label_valve", IntegerType()),
        StructField("label_pump", IntegerType()),
        StructField("label_accumulator", IntegerType()),
        StructField("label_stable", IntegerType()),
        StructField("timestamp", DoubleType())
    ])

    # Sensor data schema
    schema = StructType([
        StructField("sensor", StringType()),
        StructField("value", DoubleType()),
        StructField("cycle", IntegerType()),
        StructField("sample_idx", IntegerType()),
        StructField("timestamp", StringType()),  # ISO format string
        StructField("sampling_rate_hz", IntegerType())
    ])

    # --- READ STREAMS ---

    # 1. Read Sensor Data from Kafka
    df_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribePattern", "hydraulic-PS.*|hydraulic-FS.*|hydraulic-TS.*|hydraulic-EPS.*|hydraulic-VS.*|hydraulic-CE.*|hydraulic-CP.*|hydraulic-SE.*") \
        .option("startingOffsets", KAFKA_STARTING_OFFSETS) \
        .load()

    # 2. Read Labels from Kafka (parallel stream)
    df_labels_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", "hydraulic-labels") \
        .option("startingOffsets", "earliest") \
        .load()

    # --- TRANSFORMATION LOGIC ---

    # Parse Sensor Data
    parsed_df = df_raw.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*") \
    .withColumn("proc_time", current_timestamp()) # Use processing time for windowing in live streams if message time is unreliable

    # Add Watermarking (Important for "Intermediate" Spark requirement)
    # We allow 20 seconds of lateness
    windowed_df = parsed_df.withWatermark("proc_time", "20 seconds")

    # Aggregations (Windowing + Multiple Functions)
    # 1 minute hopping window, updated every 10 seconds
    aggregated_df = windowed_df \
        .groupBy(
            window(col("proc_time"), "1 minute", "10 seconds"),
            col("sensor")
        ) \
        .agg(
            avg("value").alias("avg_value"),
            max("value").alias("max_value"),
            min("value").alias("min_value"),
            stddev("value").alias("stddev_value"),
            (max("value") - min("value")).alias("range_value"),
            count("value").alias("sample_count")
        )

    # Format for Analytics Kafka Output
    output_df = aggregated_df.select(
        to_json(struct(
            col("sensor"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("avg_value"),
            col("max_value"),
            col("min_value"),
            col("stddev_value"),
            col("range_value"),
            col("sample_count")
        )).alias("value")
    )

    # Parse Labels
    parsed_labels = df_labels_raw.select(
        from_json(col("value").cast("string"), schema_labels).alias("data")
    ).select("data.*")

    # --- WRITE STREAMS ---

    # 1. Write Analytics back to Kafka
    query_analytics = output_df \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", "hydraulic-analytics") \
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/analytics") \
        .outputMode("update") \
        .start()

    # 2. Write Raw Sensor Data to HDFS (Parquet)
    # This fulfills the "Persistence Strategies" and "Partitioning" requirement
    query_raw_hdfs = parsed_df \
        .writeStream \
        .format("parquet") \
        .option("path", f"{HDFS_NAMENODE}/hydraulic/raw") \
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/raw_hdfs") \
        .partitionBy("sensor") \
        .outputMode("append") \
        .start()

    # 3. Write Labels to HDFS
    query_labels_hdfs = parsed_labels \
        .writeStream \
        .format("parquet") \
        .option("path", f"{HDFS_NAMENODE}/hydraulic/labels") \
        .option("checkpointLocation", f"{CHECKPOINT_DIR}/labels_hdfs") \
        .outputMode("append") \
        .start()

    print("✅ All streams started. Monitoring for termination...")
    
    # Wait for all streams to finish (usually runs indefinitely)
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()

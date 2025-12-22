
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

def main():
    spark = SparkSession.builder \
        .appName("HydraulicSystemAnalytics") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints") \
        .getOrCreate()

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

    # Define schema matches producer output
    schema = StructType([
        StructField("sensor", StringType()),
        StructField("cycle", IntegerType()),
        StructField("sample_idx", IntegerType()),
        StructField("value", DoubleType()),
        StructField("timestamp", StringType()),  # ISO format
        StructField("sampling_rate_hz", IntegerType())
    ])

    # Read from Kafka
    # Note: KAFKA_BROKER in docker network is 'kafka:29092' (INTERNAL listener)
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribePattern", "hydraulic-.*") \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON and Timestamp
    parsed = df.select(
        from_json(col("value").cast("string"), schema).alias("data"),
        col("timestamp").alias("kafka_timestamp")
    ).select("data.*") \
    .withColumn("timestamp", to_timestamp(col("timestamp"))) # Convert ISO string to Timestamp

    # Watermark for handling late data (allow 10 seconds delay)
    watermarked = parsed.withWatermark("timestamp", "10 seconds")

    # Aggregations: 1 minute hopping window (every 10 seconds)
    # Average for Pressure/Temp/Vibration (State variables)
    # Sum/Count for Flow/Power? Average is safer for general monitoring.
    aggregated = watermarked \
        .groupBy(
            window(col("timestamp"), "1 minutes", "10 seconds"),
            col("sensor")
        ) \
        .agg(
            avg("value").alias("avg_value"),
            max("value").alias("max_value"),
            min("value").alias("min_value"),
            stddev_samp("value").alias("stddev_value"),
            count("value").alias("sample_count")
        )

    # Format output for "hydraulic-analytics" topic
    # Calculate Range (Max - Min)
    output = aggregated.select(
        col("sensor").alias("key"),
        to_json(struct(
            col("sensor"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("avg_value"),
            col("max_value"),
            col("min_value"),
            col("stddev_value"),
            (col("max_value") - col("min_value")).alias("range_value"),
            col("sample_count")
        )).alias("value")
    )

    # Write back to Kafka
    # Write Analytics to Kafka
    query_analytics = output.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("topic", "hydraulic-analytics") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/analytics") \
        .outputMode("update") \
        .start()

    # Write Raw Data to HDFS (Parquet) - Requirement Satisfaction
    # Partition by 'sensor' for efficient querying
    query_hdfs = parsed.writeStream \
        .format("parquet") \
        .option("path", "hdfs://namenode:9000/hydraulic/raw") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/hdfs_raw") \
        .partitionBy("sensor") \
        .outputMode("append") \
        .start()

    # Read Labels from Kafka and Write to HDFS
    # This runs in parallel
    df_labels = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "hydraulic-labels") \
        .option("startingOffsets", "earliest") \
        .load()

    parsed_labels = df_labels.select(
        from_json(col("value").cast("string"), schema_labels).alias("data")
    ).select("data.*")

    query_labels_hdfs = parsed_labels.writeStream \
        .format("parquet") \
        .option("path", "hdfs://namenode:9000/hydraulic/labels") \
        .option("checkpointLocation", "/tmp/spark-checkpoints/hdfs_labels") \
        .trigger(processingTime='5 seconds') \
        .outputMode("append") \
        .start()

    # Wait for both
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()

import argparse
import json
import os
from typing import Any, Dict

import yaml
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (StructField, StructType, StringType, IntegerType,
                               DoubleType, TimestampType)
from dotenv import load_dotenv


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_schema() -> StructType:
    # Explicit schema for the incoming JSON events
    return StructType([
        StructField("device_id", StringType(), False),
        StructField("cycle_index", IntegerType(), True),
        StructField("event_time", StringType(), True),  # parse to timestamp later
        StructField("cooler_efficiency_pct", DoubleType(), True),
        StructField("pressure1_bar", DoubleType(), True),
        StructField("pressure2_bar", DoubleType(), True),
        StructField("temperature_cooler_out_C", DoubleType(), True),
    ])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hydraulic Spark Structured Streaming job")
    p.add_argument("--config", required=True, help="Path to streaming YAML config")
    return p.parse_args()


def write_hdfs(df: DataFrame, path: str, checkpoint: str, mode: str = "append"):
    return (
        df.writeStream.outputMode("append")
        .format("parquet")
        .option("path", path)
        .option("checkpointLocation", checkpoint + "/raw")
        .start()
    )


def write_aggregates(df: DataFrame, path: str, checkpoint: str):
    return (
        df.writeStream.outputMode("append")
        .format("parquet")
        .option("path", path)
        .option("checkpointLocation", checkpoint + "/aggregates")
        .start()
    )


def write_mongo(df: DataFrame, uri: str, database: str, collection: str, checkpoint: str, name: str):
    return (
        df.writeStream.format("mongodb")
        .option("spark.mongodb.connection.uri", uri)
        .option("spark.mongodb.database", database)
        .option("spark.mongodb.collection", collection)
        .option("checkpointLocation", f"{checkpoint}/mongo_{name}")
        .outputMode("append")
        .start()
    )


def main():
    args = parse_args()
    load_dotenv(override=True)
    cfg = load_config(args.config)

    spark = (
        SparkSession.builder.appName(cfg.get("app", {}).get("name", "HydraulicStreaming"))
        # Mongo Spark Connector
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    source_cfg = cfg.get("source", {})
    kafka_cfg = source_cfg.get("kafka", {})
    bootstrap = os.getenv("KAFKA_BROKERS", kafka_cfg.get("bootstrap_servers", "localhost:9092"))
    topic = os.getenv("KAFKA_TOPIC", kafka_cfg.get("topic", "hydraulic_sensor_data"))
    starting_offsets = kafka_cfg.get("starting_offsets", "latest")

    event_time_col = source_cfg.get("event_time_column", "event_time")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", starting_offsets)
        .load()
    )

    schema = build_schema()

    parsed = (
        raw_stream.select(F.col("key").cast("string").alias("_key"), F.col("value").cast("string").alias("json"))
        .select(F.from_json("json", schema).alias("data"))
        .select("data.*")
        .withColumn(event_time_col, F.to_timestamp(F.col(event_time_col)))
        .withWatermark(event_time_col, f"{cfg['windowing']['watermark_minutes']} minutes")
    )

    # Windowed aggregations
    window_minutes = int(cfg["windowing"]["window_minutes"])
    slide_minutes = int(cfg["windowing"]["slide_minutes"])

    windowed = (
        parsed.groupBy(
            F.window(F.col(event_time_col), f"{window_minutes} minutes", f"{slide_minutes} minutes"),
            F.col("device_id"),
        )
        .agg(
            F.avg("cooler_efficiency_pct").alias("avg_cooler_efficiency"),
            F.stddev_samp("pressure1_bar").alias("std_pressure1"),
            F.max("temperature_cooler_out_C").alias("max_temperature"),
        )
        .withColumn("window_start", F.col("window.start").cast(TimestampType()))
        .withColumn("window_end", F.col("window.end").cast(TimestampType()))
        .drop("window")
    )

    # Alerts
    alerts_cfg = cfg.get("alerts", {}).get("rules", [])
    # Default thresholds via env for convenience
    eff_min = float(os.getenv("ALERT_COOLER_EFFICIENCY_MIN_PCT", 20))
    temp_max = float(os.getenv("ALERT_TEMPERATURE_MAX_C", 75))

    alerts_df = windowed.where((F.col("avg_cooler_efficiency") < eff_min) | (F.col("max_temperature") > temp_max))
    alerts_df = alerts_df.withColumn(
        "alert_type",
        F.when(F.col("avg_cooler_efficiency") < eff_min, F.lit("efficiency_drop")).otherwise(F.lit("temperature_exceed")),
    )

    # Sinks
    sinks = cfg.get("sinks", {})
    checkpoint = cfg.get("checkpointing", {}).get("path") or os.getenv("SPARK_CHECKPOINT_DIR")
    if not checkpoint:
        raise ValueError("Checkpoint directory not configured")

    queries = []

    raw_sink = sinks.get("raw")
    if raw_sink and raw_sink.get("kind") == "hdfs":
        queries.append(write_hdfs(parsed, raw_sink["path"], checkpoint, raw_sink.get("mode", "append")))

    agg_sink = sinks.get("aggregates")
    if agg_sink and agg_sink.get("kind") == "hdfs":
        queries.append(write_aggregates(windowed, agg_sink["path"], checkpoint))

    alert_sink = sinks.get("alerts")
    if alert_sink and alert_sink.get("kind") == "mongodb":
        queries.append(
            write_mongo(
                alerts_df, alert_sink["uri"], alert_sink["database"], alert_sink["collection"], checkpoint, name="alerts"
            )
        )

    latest_sink = sinks.get("latest_metrics")
    if latest_sink and latest_sink.get("kind") == "mongodb":
        # Use complete mode with last window per device via aggregation in foreachBatch (simpler: append windowed, leave dashboard to query latest)
        queries.append(
            write_mongo(
                windowed, latest_sink["uri"], latest_sink["database"], latest_sink["collection"], checkpoint, name="latest"
            )
        )

    for q in queries:
        q.awaitTermination()


if __name__ == "__main__":
    main()

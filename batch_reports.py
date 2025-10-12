import argparse
import os
from datetime import timedelta

from dotenv import load_dotenv
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
import yaml


def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    p = argparse.ArgumentParser(description="Hydraulic batch reporting job")
    p.add_argument("--config", required=True, help="Path to batch reports YAML config")
    return p.parse_args()


def compute_last_24h_downtime(agg_df: DataFrame, lookback_hours: int, threshold: float) -> DataFrame:
    max_end = agg_df.select(F.max("window_end").alias("max_end")).collect()[0][0]
    if max_end is None:
        return agg_df.limit(0)
    window_start = F.lit(max_end - timedelta(hours=lookback_hours))
    filtered = agg_df.where(F.col("window_end") >= window_start)

    # Treat windows with avg efficiency below threshold as 'downtime'
    # Approximate downtime minutes by window length
    window_minutes = 5
    downtime = (
        filtered.where(F.col("avg_cooler_efficiency") < F.lit(threshold))
        .groupBy("device_id")
        .agg((F.count(F.lit(1)) * F.lit(window_minutes)).alias("downtime_minutes"))
        .withColumn("lookback_hours", F.lit(lookback_hours))
    )
    return downtime


def compute_weekly_temperature_trend(agg_df: DataFrame, lookback_days: int) -> DataFrame:
    max_end = agg_df.select(F.max("window_end").alias("max_end")).collect()[0][0]
    if max_end is None:
        return agg_df.limit(0)
    window_start = F.lit(max_end - timedelta(days=lookback_days))
    filtered = agg_df.where(F.col("window_end") >= window_start)

    trend = (
        filtered.groupBy("device_id", F.date_trunc("day", F.col("window_start")).alias("day"))
        .agg(F.max("max_temperature").alias("day_max_temperature"))
        .orderBy("device_id", "day")
    )
    return trend


def main():
    args = parse_args()
    load_dotenv(override=True)
    cfg = load_config(args.config)

    spark = SparkSession.builder.appName(cfg.get("job", {}).get("name", "HydraulicReports")).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    agg_path = cfg.get("source", {}).get("agg_path")
    if not agg_path:
        raise ValueError("Aggregates path not configured in reports.yaml")

    agg_df = spark.read.parquet(agg_path)

    reports_cfg = cfg.get("reports", [])
    outputs = []
    for report in reports_cfg:
        name = report.get("name")
        if name == "last_24h_downtime":
            hours = int(os.getenv("BATCH_REPORT_LOOKBACK_HOURS", report.get("lookback_hours", 24)))
            threshold = float(os.getenv("ALERT_COOLER_EFFICIENCY_MIN_PCT", report.get("logic", {}).get("below_threshold", 20)))
            outputs.append((name, compute_last_24h_downtime(agg_df, hours, threshold)))
        elif name == "weekly_temperature_trend":
            days = int(os.getenv("WEEKLY_TREND_LOOKBACK_DAYS", report.get("lookback_days", 7)))
            outputs.append((name, compute_weekly_temperature_trend(agg_df, days)))

    out_cfg = cfg.get("output", {})
    out_path = out_cfg.get("path")
    if not out_path:
        raise ValueError("Output path not configured in reports.yaml")

    for name, df in outputs:
        df.write.mode(out_cfg.get("mode", "overwrite")).format(out_cfg.get("format", "parquet")).save(f"{out_path}/{name}")

    print("Batch reports completed:", ", ".join(name for name, _ in outputs))


if __name__ == "__main__":
    main()

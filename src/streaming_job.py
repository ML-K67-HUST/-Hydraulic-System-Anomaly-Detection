#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spark Structured Streaming Job for Hydraulic System
Đọc từ Kafka, xử lý với windowing/watermarking, phát hiện bất thường,
và ghi đồng thời ra HDFS (cold) và MongoDB (hot).
"""

import yaml
import json
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, max, min, when, current_date, to_timestamp
from pyspark.sql.types import StructType


def load_config(config_path='config/spark/streaming.yaml'):
    """Tải tệp cấu hình YAML từ đường dẫn tương đối so với gốc project."""
    if not os.path.exists(config_path):
        alt_path = f"../{config_path}"
        if os.path.exists(alt_path):
            config_path = alt_path
        else:
            raise FileNotFoundError(f"Không thể tìm thấy tệp cấu hình: {config_path}")
            
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_spark_session(app_name, master, spark_ui_port):
    """Khởi tạo và trả về một SparkSession."""
    spark = SparkSession \
        .builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.ui.port", spark_ui_port) \
        .config("spark.sql.shuffle.partitions", 200) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    return spark


def load_kafka_schema(schema_path):
    """Tải schema JSON từ một tệp."""
    # Handle relative paths
    if not os.path.exists(schema_path):
        alt_path = f"../{schema_path}"
        if os.path.exists(alt_path):
            schema_path = alt_path
        else:
            raise FileNotFoundError(f"Không thể tìm thấy schema file: {schema_path}")
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_definition = json.load(f)
        print(f"Đã tải schema thành công từ: {schema_path}")
        return StructType.fromJson(schema_definition)
    except Exception as e:
        print(f"Lỗi khi tải schema từ {schema_path}: {e}")
        raise


def read_kafka_stream(spark, config):
    """Đọc và phân tích cú pháp luồng dữ liệu từ Kafka."""
    json_schema = load_kafka_schema(config['kafka']['schema_path'])
    
    # Use bootstrap_servers_host if available (for local development)
    kafka_bootstrap = config['kafka'].get('bootstrap_servers_host') or config['kafka']['bootstrap_servers']
    
    kafka_stream_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap) \
        .option("subscribe", config['kafka']['subscribe_topic']) \
        .option("startingOffsets", config['kafka']['starting_offsets']) \
        .load()

    parsed_df = kafka_stream_df \
        .select(col("value").cast("string").alias("json_value")) \
        .withColumn("data", from_json(col("json_value"), json_schema)) \
        .select("data.*")  # Mở rộng các trường JSON
    
    # Chuyển đổi timestamp - tìm cột timestamp trong schema
    timestamp_col = None
    for col_name in parsed_df.columns:
        if 'time' in col_name.lower() or 'timestamp' in col_name.lower():
            timestamp_col = col_name
            break
    
    if timestamp_col:
        parsed_df = parsed_df.withColumn("timestamp", to_timestamp(col(timestamp_col)))
    else:
        # Nếu không có timestamp, tạo từ current time
        from pyspark.sql.functions import current_timestamp
        parsed_df = parsed_df.withColumn("timestamp", current_timestamp())
    
    print("Đã thiết lập luồng đọc Kafka và phân tích cú pháp JSON.")
    return parsed_df


def apply_stream_processing(raw_df, logic_config):
    """Áp dụng windowing, watermarking và tổng hợp."""
    print(f"Áp dụng Window: {logic_config['window_duration']}, Slide: {logic_config['slide_duration']}, Watermark: {logic_config['watermark_delay']}")
    
    # Xác định device_id column
    device_col = None
    for col_name in raw_df.columns:
        if 'device' in col_name.lower() or 'sensor' in col_name.lower():
            device_col = col_name
            break
    
    if not device_col:
        # Tạo device_id từ sensor name nếu có
        if 'sensor' in raw_df.columns:
            device_col = 'sensor'
        else:
            # Fallback: tạo device_id = "hydraulic_system"
            from pyspark.sql.functions import lit
            raw_df = raw_df.withColumn("device_id", lit("hydraulic_system"))
            device_col = "device_id"
    
    # Xác định các cột để aggregate
    agg_exprs = []
    
    # Pressure
    pressure_cols = [c for c in raw_df.columns if 'pressure' in c.lower() or 'ps' in c.lower() or c == 'value']
    if pressure_cols:
        agg_exprs.append(avg(col(pressure_cols[0])).alias("avg_pressure"))
        agg_exprs.append(max(col(pressure_cols[0])).alias("max_pressure"))
    
    # Temperature
    temp_cols = [c for c in raw_df.columns if 'temperature' in c.lower() or 'temp' in c.lower()]
    if temp_cols:
        agg_exprs.append(max(col(temp_cols[0])).alias("max_temperature"))
    
    # Cooler efficiency
    cooler_cols = [c for c in raw_df.columns if 'cooler' in c.lower() or 'efficiency' in c.lower()]
    if cooler_cols:
        agg_exprs.append(min(col(cooler_cols[0])).alias("min_cooler_efficiency"))
    
    # Thêm timestamp
    agg_exprs.append(max(col("timestamp")).alias("latest_timestamp_in_window"))
    
    if not agg_exprs:
        # Fallback: aggregate tất cả numeric columns
        numeric_cols = [c for c, t in zip(raw_df.columns, raw_df.dtypes) if t[1] in ['int', 'bigint', 'float', 'double']]
        for col_name in numeric_cols[:5]:  # Limit to 5 columns
            agg_exprs.append(avg(col(col_name)).alias(f"avg_{col_name}"))
    
    # Logic từ Phase 2: Implement streaming job với windowing 
    windowed_aggregates_df = raw_df \
        .withWatermark("timestamp", logic_config['watermark_delay']) \
        .groupBy(
            col(device_col).alias("device_id"),  # Nhóm theo thiết bị
            window(col("timestamp"), 
                   logic_config['window_duration'], 
                   logic_config['slide_duration']).alias("window")
        ) \
        .agg(*agg_exprs)
    
    return windowed_aggregates_df


def apply_anomaly_rules(processed_df, rules_config):
    """Áp dụng các quy tắc phát hiện bất thường Giai đoạn 1."""
    print(f"Áp dụng quy tắc: MaxPressure={rules_config['max_pressure']}, MaxTemp={rules_config['max_temperature']}")
    
    # Logic từ Trách nhiệm: Implement anomaly detection rules 
    rules_applied_df = processed_df \
        .withColumn("is_pressure_anomaly", 
            when(col("avg_pressure").isNotNull(), col("avg_pressure") > rules_config['max_pressure'])
            .otherwise(False)
        ) \
        .withColumn("is_temp_anomaly", 
            when(col("max_temperature").isNotNull(), col("max_temperature") > rules_config['max_temperature'])
            .otherwise(False)
        ) \
        .withColumn("is_cooler_anomaly",
            when(col("min_cooler_efficiency").isNotNull(), 
                 col("min_cooler_efficiency") < rules_config.get('min_cooler_efficiency', 0.5))
            .otherwise(False)
        ) \
        .withColumn("rule_based_anomaly", 
            col("is_pressure_anomaly") | col("is_temp_anomaly") | col("is_cooler_anomaly")
        ) \
        .withColumn("alert_type", 
            when(col("is_pressure_anomaly"), "High Pressure")
            .when(col("is_temp_anomaly"), "High Temperature")
            .when(col("is_cooler_anomaly"), "Low Cooler Efficiency")
            .otherwise(None)
        )
    
    return rules_applied_df


def get_sink_writer(config):
    """Hàm nội bộ để xử lý logic ghi `foreachBatch`."""
    
    class SinkWriter:
        def __init__(self, config):
            self.config = config
            print("SinkWriter đã được khởi tạo.")

        def write_batch(self, micro_batch_df, batch_id):
            """
            Hàm được gọi bởi foreachBatch.
            Ghi đồng thời ra HDFS (Cold) và MongoDB (Hot). 
            """
            print(f"--- Bắt đầu xử lý Micro-Batch ID: {batch_id} ---")
            micro_batch_df.persist()  # Cache để tái sử dụng

            # --- 1. Ghi vào Luồng Lạnh (HDFS/Parquet) ---
            # Dành cho Người 3 (Batch) và Người 4 (ML) 
            if self.config['sinks']['cold_sink_hdfs'].get('enabled', True):
                try:
                    hdfs_config = self.config['sinks']['cold_sink_hdfs']
                    partition_col = hdfs_config.get('partition_by')
                    
                    df_to_write = micro_batch_df
                    if partition_col:
                        df_to_write = micro_batch_df.withColumn(partition_col, current_date())

                    writer = df_to_write.write.mode("append").format(hdfs_config.get('format', 'parquet'))
                    if partition_col:
                        writer = writer.partitionBy(partition_col)
                    
                    writer.save(hdfs_config['path'])
                    print(f"Batch {batch_id}: Ghi thành công vào HDFS: {hdfs_config['path']}")
                    
                except Exception as e:
                    print(f"Batch {batch_id}: LỖI khi ghi vào HDFS: {e}")
                    import traceback
                    traceback.print_exc()

            # --- 2. Ghi vào Luồng Nóng (MongoDB) ---
            # Dành cho truy vấn nhanh và cảnh báo 
            if self.config['sinks']['hot_sink_mongo'].get('enabled', True):
                mongo_config = self.config['sinks']['hot_sink_mongo']
                # Use uri_host if available (for local development)
                mongo_uri = mongo_config.get('uri_host') or mongo_config['uri']
                mongo_db = mongo_config['database']

                # a. Ghi Alerts (Chỉ ghi nếu có bất thường)
                try:
                    alerts_df = micro_batch_df.filter(col("rule_based_anomaly") == True) \
                        .select("window", "device_id", "alert_type", "avg_pressure", "max_temperature", "min_cooler_efficiency", "latest_timestamp_in_window")
                    
                    if not alerts_df.rdd.isEmpty():
                        alerts_df.write \
                            .format("mongo") \
                            .mode("append") \
                            .option("uri", mongo_uri) \
                            .option("database", mongo_db) \
                            .option("collection", mongo_config['collection_alerts']) \
                            .save()
                        print(f"Batch {batch_id}: Ghi thành công {alerts_df.count()} ALERTS vào MongoDB.")
                    else:
                        print(f"Batch {batch_id}: Không có alerts mới để ghi.")
                        
                except Exception as e:
                    print(f"Batch {batch_id}: LỖI khi ghi ALERTS vào MongoDB: {e}")
                    import traceback
                    traceback.print_exc()

                # b. Ghi Metrics mới nhất (Ghi tất cả)
                try:
                    metrics_df = micro_batch_df.select("window", "device_id", "avg_pressure", "max_temperature", "min_cooler_efficiency", "latest_timestamp_in_window")
                    
                    metrics_df.write \
                        .format("mongo") \
                        .mode("append") \
                        .option("uri", mongo_uri) \
                        .option("database", mongo_db) \
                        .option("collection", mongo_config['collection_metrics']) \
                        .save()
                    print(f"Batch {batch_id}: Ghi thành công {metrics_df.count()} METRICS vào MongoDB.")
                    
                except Exception as e:
                    print(f"Batch {batch_id}: LỖI khi ghi METRICS vào MongoDB: {e}")
                    import traceback
                    traceback.print_exc()

            micro_batch_df.unpersist()
            print(f"--- Kết thúc Micro-Batch ID: {batch_id} ---")

    # Trả về hàm (function) mà foreachBatch cần
    return SinkWriter(config).write_batch


def main():
    # Tải cấu hình
    config = load_config()
    spark_config = config['spark_app']
    
    # Khởi tạo Spark
    spark = create_spark_session(
        spark_config['name'],
        spark_config['master'],
        spark_config.get('spark_ui_port', '4040')
    )
    spark.sparkContext.setLogLevel("WARN")  # Đặt log level theo file log4j.properties
    print("Spark Session đã được khởi tạo.")
    
    # 1. Đọc luồng Kafka 
    raw_stream_df = read_kafka_stream(spark, config)
    
    # 2. Xử lý Trạng thái (Windowing & Watermarking) 
    processed_stream_df = apply_stream_processing(raw_stream_df, config['logic'])
    
    # 3. Áp dụng Logic Phát hiện Bất thường (Giai đoạn 1) 
    final_stream_df = apply_anomaly_rules(processed_stream_df, config['rules'])
    
    # 4. Thiết lập Ghi Dữ liệu (Dual Sink) bằng foreachBatch 
    sink_writer_logic = get_sink_writer(config)
    
    # 5. Khởi chạy Truy vấn
    checkpoint_location = config['processing']['checkpoint_location']
    # Nếu checkpoint location là HDFS nhưng không có HDFS, dùng local
    if checkpoint_location.startswith("hdfs://"):
        checkpoint_location = "/tmp/spark-checkpoints/streaming_job"
        print(f"Warning: HDFS not available, using local checkpoint: {checkpoint_location}")
    
    streaming_query = final_stream_df.writeStream \
        .foreachBatch(sink_writer_logic) \
        .outputMode("update") \
        .trigger(processingTime=config['processing']['trigger_interval']) \
        .option("checkpointLocation", checkpoint_location) \
        .start()
       
    print(f"Truy vấn Streaming đã bắt đầu. Checkpoint tại: {checkpoint_location}")
    print(f"Spark UI có thể truy cập tại: http://localhost:{spark_config.get('spark_ui_port', '4040')} (hoặc cổng UI của Spark Master)")
    print("Press Ctrl+C to stop")
    
    try:
        streaming_query.awaitTermination()
    except KeyboardInterrupt:
        print("\n🛑 Stopping streaming query...")
        streaming_query.stop()
        spark.stop()
        print("✅ Stopped successfully")


if __name__ == "__main__":
    main()

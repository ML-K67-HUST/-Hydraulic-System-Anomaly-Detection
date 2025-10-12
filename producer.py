import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd
import yaml
from confluent_kafka import Producer
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from dotenv import load_dotenv
import os


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_producer(bootstrap_servers: str) -> Producer:
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "enable.idempotence": True,
        "linger.ms": 5,
        "batch.num.messages": 10000,
        "compression.type": "lz4",
    }
    return Producer(conf)


def delivery_report(err, msg) -> None:
    if err is not None:
        print(f"Delivery failed for record {msg.key()}: {err}")


def maybe_load_schema(schema_path: str | None) -> Draft202012Validator | None:
    if not schema_path:
        return None
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def row_to_event(row: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
    event: Dict[str, Any] = {}
    for source_col, target_field in column_mapping.items():
        event[target_field] = row.get(source_col)
    # Include any additional features under a namespaced field if present
    return event


def iter_csv_records(csv_path: str) -> Iterable[Dict[str, Any]]:
    df = pd.read_csv(csv_path)
    for record in df.to_dict(orient="records"):
        yield record


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydraulic CSV -> Kafka producer")
    parser.add_argument("--config", required=True, help="Path to producer YAML config")
    parser.add_argument("--dry-run", action="store_true", help="Print events instead of sending")
    parser.add_argument("--validate", action="store_true", help="Validate against JSON schema")
    args = parser.parse_args()

    load_dotenv(override=True)

    config = load_config(args.config)

    bootstrap_servers = os.getenv("KAFKA_BROKERS", config.get("bootstrap_servers", "localhost:9092"))
    topic = os.getenv("KAFKA_TOPIC", config.get("topic", "hydraulic_sensor_data"))
    key_field = os.getenv("PRODUCER_KEY_FIELD", config.get("key_field", "device_id"))

    data_cfg = config.get("data", {})
    csv_path = os.getenv("PRODUCER_CSV_PATH", data_cfg.get("csv_path"))
    if not csv_path:
        raise ValueError("CSV path not provided. Set PRODUCER_CSV_PATH or data.csv_path in config.")

    event_time_column = data_cfg.get("event_time_column", "event_time")
    device_id_column = os.getenv("PRODUCER_DEVICE_ID_COLUMN", data_cfg.get("device_id_column", "device_id"))

    column_mapping = data_cfg.get("column_mapping", {})
    if event_time_column not in column_mapping.values():
        # Ensure event_time is mapped if present in CSV
        if event_time_column in column_mapping:
            pass
        else:
            column_mapping.setdefault(event_time_column, event_time_column)
    column_mapping.setdefault(device_id_column, "device_id")

    serialize_cfg = config.get("serialize", {})
    schema_path = serialize_cfg.get("schema_path")
    validator = maybe_load_schema(schema_path) if args.validate else None

    rate_cfg = config.get("rate_control", {})
    sleep_seconds = float(os.getenv("PRODUCER_SLEEP_SECONDS", rate_cfg.get("sleep_seconds", 0.005)))

    dry_run = args.dry_run
    producer = None if dry_run else build_producer(bootstrap_servers)

    sent = 0
    for csv_row in iter_csv_records(csv_path):
        event = row_to_event(csv_row, column_mapping)
        # Derive key
        key_value = event.get(key_field) or event.get("device_id") or "unknown"
        payload = json.dumps(event, separators=(",", ":"))

        if validator is not None:
            try:
                validator.validate(event)
            except ValidationError as e:
                print(f"Schema validation failed for key={key_value}: {e}")
                continue

        if dry_run:
            print(payload)
        else:
            producer.produce(
                topic=topic,
                key=str(key_value).encode("utf-8"),
                value=payload.encode("utf-8"),
                callback=delivery_report,
            )

        sent += 1
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        if not dry_run and sent % 10000 == 0:
            producer.flush()

    if not dry_run:
        producer.flush()
    print(f"Completed. Records processed: {sent}")


if __name__ == "__main__":
    main()

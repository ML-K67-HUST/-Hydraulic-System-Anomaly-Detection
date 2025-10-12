import argparse
import os
from typing import Tuple

from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import MulticlassClassificationEvaluator, RegressionEvaluator
import yaml


def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    p = argparse.ArgumentParser(description="Hydraulic ML training job")
    p.add_argument("--config", required=True, help="Path to training YAML config")
    return p.parse_args()


def build_pipeline(algo_name: str, label_col: str, features: list[str]):
    assembler = VectorAssembler(inputCols=features, outputCol="features")

    if algo_name == "decision_tree_classifier":
        label_indexer = StringIndexer(inputCol=label_col, outputCol="label", handleInvalid="keep")
        model = DecisionTreeClassifier(featuresCol="features", labelCol="label")
        pipeline = Pipeline(stages=[label_indexer, assembler, model])
        task = "classification"
    elif algo_name == "linear_regression":
        # Assume label is numeric
        model = LinearRegression(featuresCol="features", labelCol=label_col)
        pipeline = Pipeline(stages=[assembler, model])
        task = "regression"
    else:
        raise ValueError(f"Unsupported algorithm: {algo_name}")

    return pipeline, task


def main():
    args = parse_args()
    load_dotenv(override=True)
    cfg = load_config(args.config)

    spark = SparkSession.builder.appName(cfg.get("job", {}).get("name", "HydraulicTraining")).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    dataset_path = cfg.get("source", {}).get("dataset_path")
    if not dataset_path:
        raise ValueError("dataset_path not configured in training.yaml")

    label_col = os.getenv("TRAIN_LABEL_COLUMN", cfg.get("features", {}).get("label_column"))
    feature_columns_str = os.getenv("TRAIN_FEATURE_COLUMNS", cfg.get("features", {}).get("feature_columns"))
    feature_columns = [c.strip() for c in feature_columns_str.split(",")]
    test_split = float(os.getenv("TRAIN_TEST_SPLIT", cfg.get("features", {}).get("test_split", 0.2)))

    algo = os.getenv("TRAIN_ALGORITHM", cfg.get("model", {}).get("algorithm", "decision_tree_classifier"))

    df = spark.read.parquet(dataset_path)
    df = df.dropna(subset=feature_columns)

    pipeline, task = build_pipeline(algo, label_col, feature_columns)

    train_df, test_df = df.randomSplit([1 - test_split, test_split], seed=42)
    model = pipeline.fit(train_df)
    predictions = model.transform(test_df)

    metrics = {}
    if task == "classification":
        evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")
        metrics["accuracy"] = evaluator.setMetricName("accuracy").evaluate(predictions)
        metrics["f1"] = evaluator.setMetricName("f1").evaluate(predictions)
    else:
        evaluator = RegressionEvaluator(labelCol=label_col, predictionCol="prediction")
        metrics["rmse"] = evaluator.setMetricName("rmse").evaluate(predictions)
        metrics["r2"] = evaluator.setMetricName("r2").evaluate(predictions)

    out_cfg = cfg.get("output", {})
    model_path = out_cfg.get("model_path")
    metrics_path = out_cfg.get("metrics_path")
    if not model_path or not metrics_path:
        raise ValueError("Model and metrics output paths must be configured in training.yaml")

    model.write().overwrite().save(model_path)

    metrics_df = spark.createDataFrame([(k, float(v)) for k, v in metrics.items()], ["metric", "value"]).coalesce(1)
    metrics_df.write.mode("overwrite").parquet(metrics_path)

    print("Training complete. Metrics:", metrics)


if __name__ == "__main__":
    main()

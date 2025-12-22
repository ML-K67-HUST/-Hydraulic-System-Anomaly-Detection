from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import RandomForestClassifier, DecisionTreeClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
import mlflow
import mlflow.spark
import json
import os

def extract_feature_importance(model, feature_cols, model_name):
    """
    Extracts feature importance from a trained tree-based model.
    Returns a JSON filename.
    """
    try:
        importances = model.featureImportances
        feature_data = []
        for i, importance in enumerate(importances):
            feature_data.append({
                "feature": feature_cols[i],
                "importance": float(importance)
            })
        
        # Sort by importance
        feature_data.sort(key=lambda x: x["importance"], reverse=True)
        
        filename = f"/tmp/{model_name}_feature_importance.json"
        with open(filename, "w") as f:
            json.dump(feature_data, f, indent=2)
            
        print(f"📊 Feature Importance ({model_name}):")
        for item in feature_data[:5]:
            print(f"   - {item['feature']}: {item['importance']:.4f}")
            
        return filename
    except Exception as e:
        print(f"⚠️ Could not extract feature importance: {e}")
        return None

def train_and_log_model(spark, train_df, test_df, classifier, model_name, feature_cols, target_col):
    """
    Trains a specific model, evaluates metrics, and logs everything to MLflow.
    """
    print(f"\n🧠 Training {model_name}...")
    
    # Create Pipeline: Indexer -> Feature Vector is already done globally? 
    # No, our passed DF already has 'features' and 'label_cooler_indexed'.
    # So we just need the Classifier.
    
    with mlflow.start_run(run_name=model_name):
        # Log Parameters
        mlflow.log_param("model_type", model_name)
        
        # Train
        model = classifier.fit(train_df)
        print(f"✅ {model_name} Trained!")
        
        # Predict
        predictions = model.transform(test_df)
        
        # Metrics to Calculate
        metric_names = ["accuracy", "weightedPrecision", "weightedRecall", "f1"]
        for metric in metric_names:
            evaluator = MulticlassClassificationEvaluator(
                labelCol=target_col, predictionCol="prediction", metricName=metric)
            score = evaluator.evaluate(predictions)
            print(f"   👉 {metric}: {score:.4f}")
            mlflow.log_metric(metric, score)
            
        # Feature Importance
        # Extract the underlying model object (it's not a pipeline here, just the classifier)
        imp_file = extract_feature_importance(model, feature_cols, model_name)
        if imp_file:
            mlflow.log_artifact(imp_file)
            
        # Log Model
        print(f"💾 Saving {model_name} to MLflow...")
        try:
            mlflow.spark.log_model(model, model_name)
            print("🎉 Model Saved Successfully!")
        except Exception as e:
            print(f"❌ Error Saving Model: {e}")

def main():
    spark = SparkSession.builder \
        .appName("HydraulicSystemTrainer") \
        .getOrCreate()

    print("🚀 Starting Spark Trainer (Multi-Model)...")

    # 1. Load Data
    df_sensors = spark.read.parquet("hdfs://namenode:9000/hydraulic/raw")
    df_labels = spark.read.parquet("hdfs://namenode:9000/hydraulic/labels")
    print(f"📊 Data Count: Sensors={df_sensors.count()}, Labels={df_labels.count()}")

    # 2. Feature Engineering (Pivot)
    sensor_stats = df_sensors.groupBy("cycle", "sensor") \
        .agg(mean("value").alias("mean_val"), stddev("value").alias("std_val"))
        
    features_per_cycle = sensor_stats.groupBy("cycle") \
        .pivot("sensor") \
        .agg(first("mean_val").alias("mean"), first("std_val").alias("std"))
    
    # 3. Join Labels & Fill NA
    data = features_per_cycle.join(df_labels, on="cycle").na.fill(0)
    
    # 4. Vectorize Features
    label_cols = ["label_cooler", "label_valve", "label_pump", "label_accumulator", "label_stable"]
    ignore_cols = ["cycle", "timestamp", "kafka_timestamp"] + label_cols
    feature_cols = [c for c in data.columns if c not in ignore_cols]
    
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
    data_vec = assembler.transform(data)
    
    # 5. Index Target Label
    target_original = "label_cooler"
    target_indexed = "label_cooler_indexed"
    
    indexer = StringIndexer(inputCol=target_original, outputCol=target_indexed)
    indexer_model = indexer.fit(data_vec)
    data_final = indexer_model.transform(data_vec)
    
    # 6. Split Data
    train_df, test_df = data_final.randomSplit([0.8, 0.2], seed=42)
    print(f"🏋️ Train Size: {train_df.count()}, Test Size: {test_df.count()}")
    
    # 7. Define Models
    models_to_train = [
        ("RandomForest", RandomForestClassifier(labelCol=target_indexed, featuresCol="features", numTrees=20)),
        ("DecisionTree", DecisionTreeClassifier(labelCol=target_indexed, featuresCol="features"))
    ]
    
    # 8. Set MLflow Experiment
    mlflow.set_tracking_uri("http://sentiman_mlflow:5000")
    mlflow.set_experiment("hydraulic_system_health_advanced")
    
    # 9. Train Loop
    for name, clf in models_to_train:
        train_and_log_model(spark, train_df, test_df, clf, name, feature_cols, target_indexed)
        
    spark.stop()

if __name__ == "__main__":
    main()

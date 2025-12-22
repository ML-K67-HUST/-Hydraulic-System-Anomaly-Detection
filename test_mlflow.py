import mlflow
import os

mlflow.set_tracking_uri("http://sentiman_mlflow:5000")
exp_name = "test_connectivity_v3"
mlflow.set_experiment(exp_name)

print(f"Experiment: {exp_name}")
exp = mlflow.get_experiment_by_name(exp_name)
print(f"Artifact Location: {exp.artifact_location}")

print("Attempting to start run...")
with mlflow.start_run():
    mlflow.log_param("test", 456)
    print("Logged param. Now logging artifact...")
    with open("test_v3.txt", "w") as f:
        f.write("Hello MLflow V3")
    mlflow.log_artifact("test_v3.txt")
    print("Logged artifact.")

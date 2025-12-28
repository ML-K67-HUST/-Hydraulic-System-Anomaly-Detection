# -------------------------------------------------
# Base Spark image (includes Hadoop/YARN client)
# -------------------------------------------------
FROM apache/spark:3.5.0

# Switch to root to install packages
USER root

# Install dependencies for numpy and mlflow
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Pre-install Python libraries needed by the Spark jobs
RUN pip install --no-cache-dir \
    numpy==1.24.4 \
    mlflow==2.17.2

# Switch back to spark user
USER spark

# Keep the container alive – the pod will be used for spark-submit
CMD ["sleep", "infinity"]

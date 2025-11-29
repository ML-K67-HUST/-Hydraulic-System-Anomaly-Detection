# ----------------------------------------------------------------------
# 1. BASE IMAGE SELECTION
# ----------------------------------------------------------------------
# We start from the official Apache Spark image that includes Spark and PySpark.
# Note: Choose a Hadoop version that matches your cluster (you are using 3.x)
FROM apache/spark-py:v3.5.0

# Define environment variables for the cluster setup (required by the base image)
ENV SPARK_HOME /opt/spark
ENV PATH $SPARK_HOME/bin:$PATH

# ----------------------------------------------------------------------
# 2. DOWNLOAD CONNECTOR JARS (Crucial for Kafka, Avro, and MongoDB)
# ----------------------------------------------------------------------
# These JARs allow Spark to communicate with external systems.
# We download them directly into Spark's 'jars' directory.

# Kafka & Schema Registry JARs (for Avro deserialization)
RUN wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar -P ${SPARK_HOME}/jars/ && \
    wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar -P ${SPARK_HOME}/jars/ && \
    wget -q https://repo1.maven.org/maven2/io/confluent/kafka-avro-serializer/7.4.0/kafka-avro-serializer-7.4.0.jar -P ${SPARK_HOME}/jars/

# MongoDB Connector JAR
RUN wget -q https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.2.1/mongo-spark-connector_2.12-10.2.1.jar -P ${SPARK_HOME}/jars/

# ----------------------------------------------------------------------
# 3. PYTHON DEPENDENCIES
# ----------------------------------------------------------------------
# Install any Python dependencies required by pyspark-etl.py
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ----------------------------------------------------------------------
# 4. ADD APPLICATION CODE
# ----------------------------------------------------------------------
# Add the PySpark script to the container. This is the file you reference
# in your spark-submit command as "local:///app/pyspark-etl.py".
WORKDIR /app
COPY spark-job.py /app/spark-job.py

# ----------------------------------------------------------------------
# 5. ENTRYPOINT (Optional, for running the client pod)
# ----------------------------------------------------------------------
# Set the default command if the container is run without an explicit command,
# but we rely on 'sleep infinity' from the spark-client-pod.yaml for submission.
CMD ["/bin/bash"]
FROM python:3.9-slim

WORKDIR /app

# Install system utilities if needed (curl/unzip used in init containers, 
# but good to have in base image for debugging)
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
RUN pip install --no-cache-dir \
    kafka-python \
    prometheus-client \
    pymongo \
    requests

# Copy Source Code
COPY src/ /app/src/
# Note: we do not copy 'data/' because it is large and downloaded by initContainer

# Set PYTHONPATH
ENV PYTHONPATH=/app

CMD ["python", "src/producer.py"]

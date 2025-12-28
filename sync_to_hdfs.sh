#!/bin/bash

# Configuration
LOCAL_DIR="/tmp/hydraulic_data/raw"
HDFS_DEST="/hydraulic/raw"
# Dynamically find the pod name (stateful set pod usually hdfs-namenode-0)
POD_NAME="hdfs-namenode-0"

echo "==================================================="
echo "🔄 HDFS Sync Service (Local -> K8s)"
echo "From: $LOCAL_DIR"
echo "To:   hdfs://$POD_NAME:$HDFS_DEST"
echo "==================================================="

# Ensure local dir exists
mkdir -p $LOCAL_DIR

# Wait for K8s API to be ready
echo "⏳ Waiting for K8s Cluster to be ready..."
until kubectl get --raw '/healthz' &> /dev/null; do
    echo "   ... waiting for API server ..."
    sleep 5
done
echo "✅ K8s Cluster is Online!"

# Loop
while true; do
    echo "📦 [$(date +%H:%M:%S)] Syncing files..."
    
    # Check if any parquet files exist
    count=$(find $LOCAL_DIR -name "*.parquet" | wc -l)
    
    if [ "$count" -gt "0" ]; then
        # Copy folder content to a temporary buffer in the container
        # We generally copy the whole directory structure
        kubectl cp $LOCAL_DIR hdfs/$POD_NAME:/tmp/hydraulic_buffer
        
        # Move from container buffer to HDFS using 'hdfs dfs -put'
        # We verify directory inside HDFS exists first
        kubectl exec -n hdfs $POD_NAME -- hdfs dfs -mkdir -p $HDFS_DEST
        
        # Put from pod-local-fs into HDFS
        # Using -f to overwrite if needed, though usually new files have new names (part-xxxxx)
        kubectl exec -n hdfs $POD_NAME -- bash -c "hdfs dfs -put -f /tmp/hydraulic_buffer/* $HDFS_DEST/ && rm -rf /tmp/hydraulic_buffer"
        
        echo "✅ Synced files to HDFS."
    else
        echo "💤 No new parquet files found locally yet."
    fi
    
    sleep 60  # Sync every 60 seconds to save API server load
done

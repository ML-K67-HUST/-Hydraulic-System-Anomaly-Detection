#!/usr/bin/env python3
import requests
import json

GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = "admin"
GRAFANA_PASS = "admin"

def create_datasource():
    session = requests.Session()
    session.auth = (GRAFANA_USER, GRAFANA_PASS)
    
    datasource = {
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "access": "proxy",
        "isDefault": True
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        # Check if exists
        resp = session.get(f"{GRAFANA_URL}/api/datasources/name/Prometheus")
        if resp.status_code == 200:
            print("✅ Datasource 'Prometheus' already exists.")
            # Update it to be sure URL is correct
            ds_id = resp.json()['id']
            resp = session.put(f"{GRAFANA_URL}/api/datasources/{ds_id}", json=datasource, headers=headers)
            print("🔄 Updated configuration.")
        else:
            # Create
            resp = session.post(f"{GRAFANA_URL}/api/datasources", json=datasource, headers=headers)
            if resp.status_code == 200:
                print("✅ Created Datasource 'Prometheus'.")
            else:
                print(f"❌ Failed to create: {resp.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_datasource()

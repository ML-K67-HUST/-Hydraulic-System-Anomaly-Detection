from pymongo import MongoClient
import pprint
import time

# Connection Config
URI = "mongodb://admin:password123@localhost:27017"
DB_NAME = "hydraulic_system"
RAW_COLL = "sensor_readings"
ANALYTICS_COLL = "sensor_analytics"

def check_data():
    try:
        print(f"🔌 Connecting to MongoDB at {URI}...")
        client = MongoClient(URI, serverSelectionTimeoutMS=2000)
        db = client[DB_NAME]
        
        # 1. Check RAW Data
        coll_raw = db[RAW_COLL]
        count_raw = coll_raw.count_documents({})
        print(f"\n📊 RAW DATA ('{RAW_COLL}'): {count_raw:,} records")
        
        print("  Latest 2 Records:")
        cursor = coll_raw.find().sort([("_id", -1)]).limit(2)
        for doc in cursor:
            doc.pop('_id', None)
            pprint.pprint(doc)
            print("-" * 20)

        # 2. Check ANALYTICS Data
        coll_analytics = db[ANALYTICS_COLL]
        count_analytics = coll_analytics.count_documents({})
        print(f"\n🧠 ANALYTICS DATA ('{ANALYTICS_COLL}'): {count_analytics:,} records")
        
        if count_analytics == 0:
            print("⚠️  No Analytics data found in new collection yet (Waiting for Spark batch).")
        else:
            print("  Latest 2 Records:")
            cursor = coll_analytics.find().sort([("_id", -1)]).limit(2)
            for doc in cursor:
                doc.pop('_id', None)
                pprint.pprint(doc)
                print("-" * 20)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_data()

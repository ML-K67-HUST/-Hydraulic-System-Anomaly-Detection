
import json
import socket
import sys

# --- DNS Patch ---
_orig_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'kafka':
        host = '127.0.0.1'
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = new_getaddrinfo

# --- Selectors Patch ---
import selectors
if hasattr(selectors, 'KqueueSelector'):
    _orig_unregister = selectors.KqueueSelector.unregister
    def new_unregister(self, fileobj):
        try:
            return _orig_unregister(self, fileobj)
        except (ValueError, OSError):
            pass
    selectors.KqueueSelector.unregister = new_unregister

from kafka import KafkaConsumer

def main():
    print("🚀 Starting Simple Consumer...")
    topic = "hydraulic-PS1"
    
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='earliest', # Start from beginning
            enable_auto_commit=True,
            group_id='simple-test-group-v1',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"✅ Connected! Waiting for messages on '{topic}'...")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    count = 0
    try:
        for message in consumer:
            val = message.value
            count += 1
            if count % 10 == 0:
                print(f"📥 Received #{count}: {val}")
    except KeyboardInterrupt:
        print("\nstopped")

if __name__ == "__main__":
    main()

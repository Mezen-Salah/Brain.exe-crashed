"""
Monitor data loading progress in real-time.
"""

from qdrant_client import QdrantClient
import time

client = QdrantClient(url="http://localhost:6333")
collections = ['products', 'users', 'financial_kb', 'transactions']

print("=" * 80)
print("REAL-TIME DATA LOADING PROGRESS")
print("=" * 80)
print("\nRefreshing every 2 seconds... (Press Ctrl+C to stop)\n")

try:
    while True:
        timestamp = time.strftime("%H:%M:%S")
        counts = []
        
        for c in collections:
            count = client.get_collection(c).points_count
            counts.append(f"{c}: {count:,}")
        
        print(f"[{timestamp}] {' | '.join(counts)}", flush=True)
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\n\n" + "=" * 80)
    print("FINAL COUNTS:")
    print("=" * 80)
    for c in collections:
        count = client.get_collection(c).points_count
        print(f"  {c:20s}: {count:,}")
    print("=" * 80)

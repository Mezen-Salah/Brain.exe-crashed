"""
Recreate collections with correct vector dimensions.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

print("=" * 80)
print("RECREATING COLLECTIONS WITH CORRECT DIMENSIONS")
print("=" * 80)

collections = ['products', 'users', 'financial_kb', 'transactions']

for col in collections:
    print(f"\n{col}:")
    
    # Delete existing collection
    try:
        client.delete_collection(col)
        print(f"  ✅ Deleted old collection")
    except:
        print(f"  ℹ️  No existing collection to delete")
    
    # Create new collection with correct dimensions (512 for CLIP ViT-B/32)
    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=512, distance=Distance.COSINE)
    )
    print(f"  ✅ Created new collection (dim=512)")

print("\n" + "=" * 80)
print("✅ ALL COLLECTIONS RECREATED")
print("=" * 80)

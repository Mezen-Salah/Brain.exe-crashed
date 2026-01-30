"""
Delete all data from Qdrant collections to prepare for new datasets.
"""

from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

print("=" * 80)
print("DELETING ALL DATA FROM COLLECTIONS")
print("=" * 80)

# Get all collections
collections_info = client.get_collections()
collections = [col.name for col in collections_info.collections]

print(f"\nFound collections: {', '.join(collections)}")
print()

for collection_name in collections:
    # Get current count
    info = client.get_collection(collection_name)
    count_before = info.points_count
    
    print(f"📦 {collection_name}:")
    print(f"   Current count: {count_before:,}")
    
    if count_before > 0:
        # Delete all points from collection (but keep the collection structure)
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        
        # Delete all points by using a filter that matches everything
        # We'll scroll through and delete in batches
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=False,
            with_vectors=False
        )
        
        point_ids = [point.id for point in scroll_result[0]]
        
        if point_ids:
            client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
                wait=True
            )
        
        # Check if there are more points
        while scroll_result[1] is not None:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=10000,
                offset=scroll_result[1],
                with_payload=False,
                with_vectors=False
            )
            point_ids = [point.id for point in scroll_result[0]]
            if point_ids:
                client.delete(
                    collection_name=collection_name,
                    points_selector=point_ids,
                    wait=True
                )
        
        # Verify deletion
        info_after = client.get_collection(collection_name)
        count_after = info_after.points_count
        
        print(f"   After deletion: {count_after:,}")
        print(f"   ✅ Deleted {count_before:,} items")
    else:
        print(f"   Already empty")
    print()

print("=" * 80)
print("✅ ALL DATA DELETED - Collections are empty and ready for new data")
print("=" * 80)
print("\nYou can now provide:")
print("  1. Products dataset")
print("  2. User profiles")
print("  3. Financial knowledge base")
print("  4. Transaction history")
print("=" * 80)

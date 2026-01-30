"""
Remove duplicate products from Qdrant based on product_id
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qdrant_client import QdrantClient
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRODUCTS_COLLECTION = "products"


def remove_duplicates():
    """Remove duplicate products, keeping only one instance of each product_id"""
    
    qdrant_client = QdrantClient(host="localhost", port=6333)
    
    print("=" * 80)
    print("🧹 REMOVING DUPLICATE PRODUCTS")
    print("=" * 80)
    print()
    
    # Step 1: Fetch all products
    print("📥 Step 1: Fetching all products...")
    
    all_points = []
    offset = None
    
    while True:
        scroll_result = qdrant_client.scroll(
            collection_name=PRODUCTS_COLLECTION,
            limit=1000,
            offset=offset,
            with_payload=True
        )
        
        points = scroll_result[0]
        offset = scroll_result[1]
        
        all_points.extend(points)
        
        if offset is None:
            break
    
    total_points = len(all_points)
    print(f"   ✅ Found {total_points} total products")
    print()
    
    # Step 2: Identify duplicates
    print("🔍 Step 2: Identifying duplicates...")
    
    product_map = defaultdict(list)
    
    for point in all_points:
        product_id = point.payload.get('product_id', '')
        product_map[product_id].append(point.id)
    
    duplicates_to_delete = []
    duplicate_count = 0
    
    for product_id, uuids in product_map.items():
        if len(uuids) > 1:
            # Keep the first UUID, delete the rest
            duplicates_to_delete.extend(uuids[1:])
            duplicate_count += len(uuids) - 1
            print(f"   Found {len(uuids)} copies of {product_id}")
    
    print(f"   ✅ Identified {duplicate_count} duplicate products to delete")
    print()
    
    # Step 3: Delete duplicates
    if duplicates_to_delete:
        print("🗑️  Step 3: Deleting duplicates...")
        
        # Delete in batches of 1000
        batch_size = 1000
        for i in range(0, len(duplicates_to_delete), batch_size):
            batch = duplicates_to_delete[i:i + batch_size]
            qdrant_client.delete(
                collection_name=PRODUCTS_COLLECTION,
                points_selector=batch
            )
            print(f"   Deleted batch {i//batch_size + 1} ({len(batch)} products)")
        
        print(f"   ✅ Deleted {len(duplicates_to_delete)} duplicate products")
        print()
    else:
        print("   ℹ️  No duplicates to delete")
        print()
    
    # Step 4: Verify deletion
    print("🔍 Step 4: Verifying deletion...")
    
    collection_info = qdrant_client.get_collection(PRODUCTS_COLLECTION)
    final_count = collection_info.points_count
    
    print(f"   ✅ Products collection now has {final_count} points")
    print()
    
    print("=" * 80)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 80)
    print()
    print(f"📈 Summary:")
    print(f"   • Duplicates deleted: {duplicate_count}")
    print(f"   • Unique products remaining: {final_count}")
    print()


if __name__ == "__main__":
    remove_duplicates()

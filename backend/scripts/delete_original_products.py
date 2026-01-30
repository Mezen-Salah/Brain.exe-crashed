"""
Delete the 8 original sample products from Qdrant, keeping only the 50K Tunisian products
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRODUCTS_COLLECTION = "products"


def delete_original_products():
    """Delete products that don't match the Tunisian product ID pattern"""
    
    qdrant_client = QdrantClient(host="localhost", port=6333)
    
    print("=" * 80)
    print("🗑️  DELETING ORIGINAL SAMPLE PRODUCTS")
    print("=" * 80)
    print()
    
    # Step 1: Get all products
    print("📥 Step 1: Fetching all products...")
    
    # Scroll through all products
    scroll_result = qdrant_client.scroll(
        collection_name=PRODUCTS_COLLECTION,
        limit=10000,
        with_payload=True
    )
    
    points = scroll_result[0]
    total_points = len(points)
    
    print(f"   ✅ Found {total_points} total products")
    print()
    
    # Step 2: Identify original products (not matching Tunisian ID pattern)
    print("🔍 Step 2: Identifying original products...")
    
    original_product_ids = []
    tunisian_prefixes = ['LAPTOP-', 'PHONE-', 'TABLET-', 'TV-', 'ACC-']
    
    for point in points:
        product_id = point.payload.get('product_id', '')
        
        # Check if it's a Tunisian product ID
        is_tunisian = any(product_id.startswith(prefix) for prefix in tunisian_prefixes)
        
        if not is_tunisian:
            original_product_ids.append(point.id)
            print(f"   Found original product: {product_id} (UUID: {point.id})")
    
    print(f"   ✅ Identified {len(original_product_ids)} original products to delete")
    print()
    
    # Step 3: Delete original products
    if original_product_ids:
        print("🗑️  Step 3: Deleting original products...")
        
        qdrant_client.delete(
            collection_name=PRODUCTS_COLLECTION,
            points_selector=original_product_ids
        )
        
        print(f"   ✅ Deleted {len(original_product_ids)} original products")
        print()
    else:
        print("   ℹ️  No original products to delete")
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
    print(f"   • Original products deleted: {len(original_product_ids)}")
    print(f"   • Tunisian products remaining: {final_count}")
    print()


if __name__ == "__main__":
    delete_original_products()

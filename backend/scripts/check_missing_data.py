"""
Check for missing or invalid data fields in the product database.
"""

import asyncio
import logging
from qdrant_client import QdrantClient
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_missing_data():
    client = QdrantClient(url="http://localhost:6333")
    
    logger.info("Scanning all products for missing data...")
    
    all_products = []
    offset = None
    
    while True:
        result = client.scroll(
            collection_name="products",
            limit=1000,
            offset=offset,
            with_payload=True
        )
        
        products_batch = result[0]
        if not products_batch:
            break
        
        all_products.extend(products_batch)
        offset = result[1]
        
        if offset is None:
            break
        
        logger.info(f"Scanned {len(all_products)} products...")
    
    logger.info(f"Total products: {len(all_products)}\n")
    
    # Analyze data quality
    missing_screen = 0
    missing_processor = 0
    missing_ram = 0
    missing_storage = 0
    zero_price = 0
    empty_model = 0
    
    issues_by_category = Counter()
    
    for point in all_products:
        p = point.payload
        
        # Check missing fields
        if not p.get('screen_size') or p.get('screen_size') == 0:
            missing_screen += 1
            issues_by_category[p.get('category', 'Unknown')] += 1
        
        if not p.get('processor') or p.get('processor').strip() == '':
            missing_processor += 1
        
        if not p.get('ram') or p.get('ram') == 0:
            missing_ram += 1
        
        if not p.get('storage') or p.get('storage') == 0:
            missing_storage += 1
        
        if not p.get('price') or p.get('price') == 0:
            zero_price += 1
        
        if not p.get('model') or p.get('model').strip() == '':
            empty_model += 1
    
    print("=" * 80)
    print("DATA QUALITY REPORT - MISSING/INVALID FIELDS")
    print("=" * 80)
    print(f"Total products scanned: {len(all_products)}")
    print()
    print("Missing/Invalid Data:")
    print(f"  - Screen size = 0 or missing:  {missing_screen:,} ({missing_screen/len(all_products)*100:.1f}%)")
    print(f"  - Processor empty:             {missing_processor:,} ({missing_processor/len(all_products)*100:.1f}%)")
    print(f"  - RAM = 0 or missing:          {missing_ram:,} ({missing_ram/len(all_products)*100:.1f}%)")
    print(f"  - Storage = 0 or missing:      {missing_storage:,} ({missing_storage/len(all_products)*100:.1f}%)")
    print(f"  - Price = 0 or missing:        {zero_price:,} ({zero_price/len(all_products)*100:.1f}%)")
    print(f"  - Model name empty:            {empty_model:,} ({empty_model/len(all_products)*100:.1f}%)")
    
    if missing_screen > 0:
        print("\nProducts with missing screen sizes by category:")
        for category, count in issues_by_category.most_common():
            print(f"  - {category}: {count:,}")
    
    print("=" * 80)
    
    total_issues = missing_screen + missing_processor + missing_ram + missing_storage + zero_price + empty_model
    
    if total_issues == 0:
        print("\n✅ All products have complete data!")
    else:
        print(f"\n⚠️  Found {total_issues:,} data quality issues")
        print("   These are missing/incomplete fields, not logical contradictions.")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_missing_data())

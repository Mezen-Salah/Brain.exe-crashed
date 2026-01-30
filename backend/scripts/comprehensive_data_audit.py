"""
Comprehensive data quality check - looking for ANY issues.
"""

import asyncio
import logging
from qdrant_client import QdrantClient
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def comprehensive_data_check():
    client = QdrantClient(url="http://localhost:6333")
    
    print("=" * 80)
    print("COMPREHENSIVE DATA QUALITY AUDIT")
    print("=" * 80)
    
    logger.info("Scanning all products for data quality issues...\n")
    
    # Track various issues
    issues = {
        'missing_name': [],
        'missing_brand': [],
        'missing_category': [],
        'missing_price': [],
        'zero_price': [],
        'negative_price': [],
        'missing_specifications': [],
        'empty_specifications': [],
        'missing_images': [],
        'duplicate_ids': [],
        'invalid_discount': [],
        'negative_stock': [],
        'missing_description': [],
    }
    
    all_products = []
    product_ids = Counter()
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
        
        for point in products_batch:
            p = point.payload
            all_products.append(point)
            
            # Track product IDs for duplicates
            product_id = p.get('product_id', '')
            if product_id:
                product_ids[product_id] += 1
            
            # Check 1: Missing critical fields
            if not p.get('name') or p.get('name', '').strip() == '':
                issues['missing_name'].append(point.id)
            
            if not p.get('brand') or p.get('brand', '').strip() == '':
                issues['missing_brand'].append(point.id)
            
            if not p.get('category') or p.get('category', '').strip() == '':
                issues['missing_category'].append(point.id)
            
            if not p.get('description') or p.get('description', '').strip() == '':
                issues['missing_description'].append(point.id)
            
            # Check 2: Price issues
            price = p.get('price', 0)
            if price is None or price == 0:
                issues['zero_price'].append(point.id)
            elif price < 0:
                issues['negative_price'].append(point.id)
            
            if not p.get('price'):
                issues['missing_price'].append(point.id)
            
            # Check 3: Specifications
            specs = p.get('specifications')
            if specs is None:
                issues['missing_specifications'].append(point.id)
            elif isinstance(specs, dict) and len(specs) == 0:
                issues['empty_specifications'].append(point.id)
            
            # Check 4: Images
            main_image = p.get('main_image', '')
            images = p.get('images', [])
            if not main_image and not images:
                issues['missing_images'].append(point.id)
            
            # Check 5: Invalid discount
            discount = p.get('discount_percentage', 0)
            if discount < 0 or discount > 100:
                issues['invalid_discount'].append(point.id)
            
            # Check 6: Stock quantity
            stock = p.get('stock_quantity', 0)
            if stock < 0:
                issues['negative_stock'].append(point.id)
        
        offset = result[1]
        if offset is None:
            break
        
        if len(all_products) % 5000 == 0:
            logger.info(f"Scanned {len(all_products):,} products...")
    
    # Check for duplicate product IDs
    for pid, count in product_ids.items():
        if count > 1:
            issues['duplicate_ids'].append(f"{pid} (appears {count} times)")
    
    logger.info(f"Completed scanning {len(all_products):,} products\n")
    
    # Report results
    print("=" * 80)
    print("DATA QUALITY REPORT")
    print("=" * 80)
    print(f"Total products scanned: {len(all_products):,}\n")
    
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("✅ PERFECT: NO DATA QUALITY ISSUES FOUND!\n")
        print("All checks passed:")
        print("  ✓ All products have name, brand, category")
        print("  ✓ All prices are valid (>0)")
        print("  ✓ All products have specifications")
        print("  ✓ All products have images")
        print("  ✓ No duplicate product IDs")
        print("  ✓ All discounts are valid (0-100%)")
        print("  ✓ All stock quantities are valid (≥0)")
        print("  ✓ All products have descriptions")
    else:
        print(f"⚠️  FOUND {total_issues:,} DATA QUALITY ISSUES:\n")
        
        for issue_type, issue_list in issues.items():
            if issue_list:
                count = len(issue_list)
                percentage = (count / len(all_products)) * 100
                print(f"  • {issue_type.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
                
                # Show examples for first few issues
                if issue_type == 'duplicate_ids':
                    for dup in issue_list[:3]:
                        print(f"      - {dup}")
                    if len(issue_list) > 3:
                        print(f"      ... and {len(issue_list) - 3} more")
        
        print()
    
    print("=" * 80)
    
    # Additional statistics
    print("\nDATA STATISTICS:")
    
    # Category distribution
    categories = Counter([p.payload.get('category', 'Unknown') for p in all_products])
    print("\nProducts by category:")
    for cat, count in categories.most_common():
        print(f"  - {cat}: {count:,} ({count/len(all_products)*100:.1f}%)")
    
    # Brand distribution (top 10)
    brands = Counter([p.payload.get('brand', 'Unknown') for p in all_products])
    print("\nTop 10 brands:")
    for brand, count in brands.most_common(10):
        print(f"  - {brand}: {count:,}")
    
    # Price range
    prices = [p.payload.get('price', 0) for p in all_products if p.payload.get('price', 0) > 0]
    if prices:
        print(f"\nPrice range:")
        print(f"  - Minimum: {min(prices):,.2f} TND")
        print(f"  - Maximum: {max(prices):,.2f} TND")
        print(f"  - Average: {sum(prices)/len(prices):,.2f} TND")
    
    print("=" * 80)
    
    return total_issues == 0


if __name__ == "__main__":
    result = asyncio.run(comprehensive_data_check())
    exit(0 if result else 1)

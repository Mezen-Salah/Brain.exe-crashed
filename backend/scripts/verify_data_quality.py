"""
Verify data quality after cleaning illogical products.
"""

import asyncio
import logging
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BRAND_MODELS = {
    'MacBook': ['Apple'],
    'iPad': ['Apple'],
    'Surface': ['Microsoft'],
    'Galaxy': ['Samsung'],
    'IdeaPad': ['Lenovo'],
    'ThinkPad': ['Lenovo'],
    'VivoBook': ['Asus'],
    'ZenBook': ['Asus'],
    'Aspire': ['Acer'],
    'Pavilion': ['HP'],
    'Inspiron': ['Dell'],
    'XPS': ['Dell'],
}

async def verify_products():
    client = QdrantClient(url="http://localhost:6333")
    
    # Get a sample of 100 products
    logger.info("Fetching sample of 100 products...")
    result = client.scroll(
        collection_name="products",
        limit=100,
        with_payload=True
    )
    
    products = result[0]
    logger.info(f"Retrieved {len(products)} products\n")
    
    print("=" * 80)
    print("PRODUCT DATA QUALITY VERIFICATION")
    print("=" * 80)
    
    issues = []
    
    for point in products:
        payload = point.payload
        product_id = point.id
        brand = payload.get('brand', '').lower()
        model = payload.get('model', '')
        
        # CORRECTED: Read from specifications object
        specs = payload.get('specifications', {})
        processor = specs.get('processor', '')
        screen_size_str = specs.get('screen_size', '')
        
        # Try to parse screen size
        screen_size = 0
        if screen_size_str:
            try:
                screen_size = float(screen_size_str.replace('pouces', '').replace('"', '').strip().split()[0])
            except:
                screen_size = 0
        
        category = payload.get('category', '')
        
        problem = None
        
        # Check 1: Brand-Model mismatch
        for model_keyword, allowed_brands in BRAND_MODELS.items():
            if model_keyword in model:
                allowed = [b.lower() for b in allowed_brands]
                if brand not in allowed:
                    problem = f"Brand mismatch: {brand} cannot make {model_keyword}"
                    break
        
        # Check 2: Apple processor on non-Apple product
        if not problem and any(chip in processor for chip in ['M1', 'M2', 'M3', 'M4']):
            if brand != 'apple':
                problem = f"Non-Apple brand ({brand}) with Apple chip ({processor})"
        
        # Check 3: Non-Apple processor on Apple product
        if not problem and brand == 'apple':
            if any(chip in processor.lower() for chip in ['intel', 'amd', 'ryzen']):
                problem = f"Apple product with non-Apple chip ({processor})"
        
        # Check 4: Screen size validation
        if not problem:
            if category == 'Smartphones' and screen_size > 8:
                problem = f"Smartphone with {screen_size}\" screen (max 8\")"
            elif category == 'Tablettes' and (screen_size < 7 or screen_size > 15):
                problem = f"Tablet with {screen_size}\" screen (must be 7-15\")"
            elif category in ['Laptops', 'Ordinateurs Portables']:
                if screen_size < 11 or screen_size > 18:
                    problem = f"Laptop with {screen_size}\" screen (must be 11-18\")"
        
        if problem:
            issues.append({
                'id': product_id,
                'brand': brand,
                'model': model,
                'processor': processor,
                'category': category,
                'screen_size': screen_size,
                'problem': problem
            })
            print(f"\n❌ ISSUE FOUND:")
            print(f"   Product ID: {product_id}")
            print(f"   {brand.title()} {model}")
            print(f"   Processor: {processor}")
            print(f"   Category: {category}, Screen: {screen_size}\"")
            print(f"   Problem: {problem}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Products checked: {len(products)}")
    print(f"Issues found: {len(issues)}")
    
    if len(issues) == 0:
        print("\n✅ SUCCESS: All sampled products appear to be valid!")
        print("   No brand-model mismatches detected")
        print("   No processor mismatches detected")
        print("   No screen size violations detected")
    else:
        print(f"\n⚠️  WARNING: Found {len(issues)} potentially illogical products")
        print(f"   This represents {len(issues)/len(products)*100:.1f}% of the sample")
        print("\n   Most common issues:")
        issue_types = {}
        for issue in issues:
            prob_type = issue['problem'].split(':')[0]
            issue_types[prob_type] = issue_types.get(prob_type, 0) + 1
        
        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {issue_type}: {count} products")
    
    print("=" * 80)
    
    return len(issues)

if __name__ == "__main__":
    issues_count = asyncio.run(verify_products())
    exit(0 if issues_count == 0 else 1)

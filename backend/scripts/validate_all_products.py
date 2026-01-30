"""
Validate ALL products in the database - comprehensive check.
"""

import asyncio
import logging
from qdrant_client import QdrantClient
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductValidator:
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
    
    APPLE_PROCESSORS = ['M1', 'M2', 'M3', 'M4', 'A14', 'A15', 'A16', 'A17']
    
    def is_valid(self, product: dict) -> tuple[bool, str]:
        """Check if a product is logically valid."""
        brand = product.get('brand', '').lower()
        model = product.get('model', '')
        name = product.get('name', '')
        category = product.get('category', '')
        
        # Read from specifications object
        specs = product.get('specifications', {})
        processor = specs.get('processor', '')
        screen_size_str = specs.get('screen_size', '')
        
        # Check 1: Brand-Model mismatch
        for model_name, valid_brands in self.BRAND_MODELS.items():
            if model_name.lower() in model.lower() or model_name.lower() in name.lower():
                valid_brands_lower = [b.lower() for b in valid_brands]
                if brand not in valid_brands_lower:
                    return False, f"Brand mismatch: {brand} cannot make {model_name}"
        
        # Check 2: Apple processor on non-Apple product
        if brand != 'apple' and processor:
            for apple_proc in self.APPLE_PROCESSORS:
                if apple_proc in processor:
                    return False, f"Non-Apple brand with Apple chip: {brand} with {processor}"
        
        # Check 3: Non-Apple processor on Apple product  
        if brand == 'apple' and processor:
            has_apple_chip = any(chip in processor for chip in self.APPLE_PROCESSORS)
            has_intel_amd = any(chip in processor.lower() for chip in ['intel', 'amd', 'ryzen'])
            if has_intel_amd and not has_apple_chip:
                return False, f"Apple product with non-Apple chip: {processor}"
        
        # Check 4: Screen size validation (only if we have the data)
        if screen_size_str:
            try:
                # Extract number from strings like "15.6 pouces" or "15.6\""
                size_str = screen_size_str.replace('pouces', '').replace('"', '').strip()
                size = float(size_str.split()[0])
                
                if 'smartphone' in category.lower() or 'téléphone' in category.lower():
                    if size > 8.0:
                        return False, f"Smartphone with {size}\" screen (max 8\")"
                
                elif 'tablet' in category.lower() or 'tablette' in category.lower():
                    if size < 7.0 or size > 15.0:
                        return False, f"Tablet with {size}\" screen (must be 7-15\")"
                
                elif 'laptop' in category.lower() or 'ordinateur' in category.lower():
                    if size < 11.0 or size > 18.0:
                        return False, f"Laptop with {size}\" screen (must be 11-18\")"
            except (ValueError, IndexError):
                pass  # Skip if we can't parse screen size
        
        return True, ""


async def validate_all_products():
    client = QdrantClient(url="http://localhost:6333")
    validator = ProductValidator()
    
    print("=" * 80)
    print("COMPREHENSIVE VALIDATION - CHECKING ALL PRODUCTS")
    print("=" * 80)
    
    logger.info("Fetching collection info...")
    collection_info = client.get_collection("products")
    total_products = collection_info.points_count
    
    logger.info(f"Total products to validate: {total_products:,}\n")
    
    all_products = []
    invalid_products = []
    offset = None
    batch_num = 0
    
    # Scan all products
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
        
        batch_num += 1
        
        for point in products_batch:
            all_products.append(point)
            is_valid, reason = validator.is_valid(point.payload)
            
            if not is_valid:
                invalid_products.append({
                    'id': point.id,
                    'name': point.payload.get('name', 'Unknown'),
                    'brand': point.payload.get('brand', ''),
                    'reason': reason
                })
        
        offset = result[1]
        if offset is None:
            break
        
        # Progress update every 5 batches (5000 products)
        if batch_num % 5 == 0:
            logger.info(f"Progress: {len(all_products):,}/{total_products:,} products scanned, {len(invalid_products)} issues found...")
    
    logger.info(f"Completed scanning all {len(all_products):,} products\n")
    
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print(f"Total products scanned: {len(all_products):,}")
    print(f"Invalid products found: {len(invalid_products):,}")
    print(f"Valid products: {len(all_products) - len(invalid_products):,}")
    print(f"Success rate: {((len(all_products) - len(invalid_products))/len(all_products)*100):.2f}%")
    print("=" * 80)
    
    if invalid_products:
        print("\n⚠️  ISSUES DETECTED:\n")
        
        # Group by reason
        reasons = Counter([p['reason'] for p in invalid_products])
        print("Issue breakdown:")
        for reason, count in reasons.most_common():
            print(f"  - {reason}: {count}")
        
        print("\nFirst 20 invalid products:")
        for i, product in enumerate(invalid_products[:20], 1):
            print(f"  {i}. {product['brand'].title()} {product['name']}")
            print(f"     Reason: {product['reason']}")
        
        if len(invalid_products) > 20:
            print(f"  ... and {len(invalid_products) - 20} more")
        
        print("\n" + "=" * 80)
        print(f"❌ VALIDATION FAILED: {len(invalid_products)} illogical products found")
        print("=" * 80)
        return False
    else:
        print(f"\n✅ SUCCESS: ALL {len(all_products):,} PRODUCTS ARE VALID!")
        print("\nValidation checks passed:")
        print("  ✓ No brand-model mismatches (MacBook only Apple, ThinkPad only Lenovo, etc.)")
        print("  ✓ No processor mismatches (Apple chips only on Apple products)")
        print("  ✓ No screen size violations (smartphones <8\", tablets 7-15\", laptops 11-18\")")
        print("  ✓ All products are logically consistent")
        print("=" * 80)
        return True


if __name__ == "__main__":
    result = asyncio.run(validate_all_products())
    exit(0 if result else 1)

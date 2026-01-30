"""
CORRECTED VERSION: Clean illogical products from the database.
This version correctly reads from the 'specifications' object.
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
        
        # CORRECTED: Read from specifications object
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


async def scan_and_delete():
    client = QdrantClient(url="http://localhost:6333")
    validator = ProductValidator()
    
    logger.info("Scanning all products for logical issues...")
    
    all_products = []
    invalid_products = []
    offset = None
    deletion_reasons = Counter()
    
    while True:
        result = client.scroll(
            collection_name="products",
            limit=100,
            offset=offset,
            with_payload=True
        )
        
        products_batch = result[0]
        if not products_batch:
            break
        
        for point in products_batch:
            all_products.append(point)
            is_valid, reason = validator.is_valid(point.payload)
            
            if not is_valid:
                invalid_products.append(point.id)
                deletion_reasons[reason] += 1
                logger.info(f"❌ Invalid: {point.payload.get('name', 'Unknown')} - {reason}")
        
        offset = result[1]
        if offset is None:
            break
        
        if len(all_products) % 1000 == 0:
            logger.info(f"Scanned {len(all_products)} products, found {len(invalid_products)} invalid...")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Validation complete!")
    logger.info(f"Total scanned: {len(all_products)}")
    logger.info(f"Invalid products found: {len(invalid_products)}")
    logger.info(f"Valid products: {len(all_products) - len(invalid_products)}")
    logger.info(f"{'='*60}\n")
    
    if invalid_products:
        logger.info(f"Deletion reasons breakdown:")
        for reason, count in deletion_reasons.most_common():
            logger.info(f"  - {reason}: {count}")
        
        logger.info(f"\nDeleting {len(invalid_products)} invalid products...")
        
        # Delete in batches of 100
        batch_size = 100
        for i in range(0, len(invalid_products), batch_size):
            batch = invalid_products[i:i + batch_size]
            client.delete(
                collection_name="products",
                points_selector=batch,
                wait=True
            )
            logger.info(f"Deleted batch {i//batch_size + 1}/{(len(invalid_products) + batch_size - 1)//batch_size}")
        
        logger.info(f"✅ Successfully deleted {len(invalid_products)} invalid products")
        logger.info(f"✅ Remaining products: {len(all_products) - len(invalid_products)}")
    else:
        logger.info("✅ No illogical products found!")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL RESULTS:")
    logger.info(f"  Total products scanned: {len(all_products)}")
    logger.info(f"  Invalid products deleted: {len(invalid_products)}")
    logger.info(f"  Valid products remaining: {len(all_products) - len(invalid_products)}")
    logger.info(f"  Data quality: {((len(all_products) - len(invalid_products))/len(all_products)*100):.1f}%")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(scan_and_delete())

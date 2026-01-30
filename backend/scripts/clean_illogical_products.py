"""
Clean illogical products from Qdrant database
Removes products with impossible brand/model/spec combinations
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.qdrant_client import qdrant_manager
from core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductValidator:
    """Validates product logical consistency"""
    
    # Brand-specific model names
    BRAND_MODELS = {
        'MacBook': ['Apple'],
        'iPad': ['Apple'],
        'iPhone': ['Apple'],
        'Surface': ['Microsoft'],
        'IdeaPad': ['Lenovo'],
        'ThinkPad': ['Lenovo'],
        'VivoBook': ['Asus'],
        'ZenBook': ['Asus'],
        'Aspire': ['Acer'],
        'Predator': ['Acer'],
        'Pavilion': ['HP'],
        'Inspiron': ['Dell'],
        'XPS': ['Dell'],
        'Galaxy': ['Samsung'],
    }
    
    # Processor restrictions
    APPLE_PROCESSORS = ['M1', 'M2', 'M3', 'M4', 'Apple M']
    NON_APPLE_PROCESSORS = ['Intel', 'AMD', 'Ryzen', 'Core i', 'Snapdragon', 'MediaTek']
    
    def __init__(self):
        self.deleted_count = 0
        self.deleted_reasons = {}
    
    def is_valid(self, product: dict) -> tuple[bool, str]:
        """
        Check if product has logical consistency
        
        Returns:
            (is_valid, reason_if_invalid)
        """
        name = product.get('name', '').lower()
        brand = product.get('brand', '').lower()
        model = product.get('model', '')
        processor = product.get('processor', '')
        category = product.get('category', '')
        subcategory = product.get('subcategory', '')
        
        # Check 1: Brand-Model mismatch
        for model_name, valid_brands in self.BRAND_MODELS.items():
            if model_name.lower() in name or model_name.lower() in model:
                valid_brands_lower = [b.lower() for b in valid_brands]
                if brand not in valid_brands_lower:
                    return False, f"Brand mismatch: {brand} cannot make {model_name}"
        
        # Check 2: Apple processor on non-Apple product
        if brand != 'apple':
            for apple_proc in self.APPLE_PROCESSORS:
                if apple_proc.lower() in processor.lower():
                    return False, f"Non-Apple brand with Apple chip: {brand} with {processor}"
        
        # Check 3: Apple product with non-Apple processor
        if brand == 'apple':
            has_non_apple_proc = any(proc.lower() in processor.lower() for proc in self.NON_APPLE_PROCESSORS)
            if has_non_apple_proc and 'M1' not in processor and 'M2' not in processor and 'M3' not in processor:
                return False, f"Apple product with non-Apple chip: {processor}"
        
        # Check 4: Screen size logic (smartphones)
        if 'smartphone' in category.lower() or 'téléphone' in category.lower():
            screen_size = product.get('screen_size', '')
            if screen_size:
                try:
                    # Extract numeric value
                    size = float(screen_size.replace('"', '').replace('pouces', '').strip().split()[0])
                    if size > 8.0:  # Smartphones shouldn't exceed 8 inches
                        return False, f"Smartphone with impossible screen size: {screen_size}"
                except:
                    pass
        
        # Check 5: Screen size logic (tablets)
        if 'tablet' in category.lower() or 'tablette' in category.lower():
            screen_size = product.get('screen_size', '')
            if screen_size:
                try:
                    size = float(screen_size.replace('"', '').replace('pouces', '').strip().split()[0])
                    if size < 7.0 or size > 15.0:  # Tablets between 7-15 inches
                        return False, f"Tablet with impossible screen size: {screen_size}"
                except:
                    pass
        
        # Check 6: Screen size logic (laptops)
        if 'ordinateur' in category.lower() or 'laptop' in name:
            screen_size = product.get('screen_size', '')
            if screen_size:
                try:
                    size = float(screen_size.replace('"', '').replace('pouces', '').strip().split()[0])
                    if size < 11.0 or size > 18.0:  # Laptops between 11-18 inches
                        return False, f"Laptop with impossible screen size: {screen_size}"
                except:
                    pass
        
        return True, ""
    
    def validate_and_clean(self):
        """Scan all products and delete illogical ones"""
        collection_name = settings.qdrant_collection_products
        
        logger.info("Starting product validation...")
        logger.info("Fetching all products from Qdrant...")
        
        offset = None
        batch_size = 100
        total_scanned = 0
        to_delete = []
        
        while True:
            # Scroll through products
            result, next_offset = qdrant_manager.client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            if not result:
                break
            
            # Validate each product
            for point in result:
                total_scanned += 1
                product = point.payload
                
                is_valid, reason = self.is_valid(product)
                
                if not is_valid:
                    to_delete.append(point.id)
                    
                    # Track deletion reasons
                    if reason not in self.deleted_reasons:
                        self.deleted_reasons[reason] = 0
                    self.deleted_reasons[reason] += 1
                    
                    logger.info(f"❌ Invalid: {product.get('name', 'Unknown')} - {reason}")
            
            if total_scanned % 1000 == 0:
                logger.info(f"Scanned {total_scanned} products, found {len(to_delete)} invalid...")
            
            # Check if there are more products
            if next_offset is None:
                break
            offset = next_offset
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Validation complete!")
        logger.info(f"Total scanned: {total_scanned}")
        logger.info(f"Invalid products found: {len(to_delete)}")
        logger.info(f"Valid products: {total_scanned - len(to_delete)}")
        logger.info(f"{'='*60}\n")
        
        # Show deletion reasons summary
        logger.info("Deletion reasons breakdown:")
        for reason, count in sorted(self.deleted_reasons.items(), key=lambda x: -x[1]):
            logger.info(f"  - {reason}: {count}")
        
        # Delete invalid products
        if to_delete:
            logger.info(f"\nDeleting {len(to_delete)} invalid products...")
            
            # Delete in batches of 100
            batch_size = 100
            for i in range(0, len(to_delete), batch_size):
                batch = to_delete[i:i+batch_size]
                qdrant_manager.client.delete(
                    collection_name=collection_name,
                    points_selector=batch
                )
                logger.info(f"Deleted batch {i//batch_size + 1}/{(len(to_delete)-1)//batch_size + 1}")
            
            logger.info(f"✅ Successfully deleted {len(to_delete)} invalid products")
            logger.info(f"✅ Remaining products: {total_scanned - len(to_delete)}")
        else:
            logger.info("✅ No invalid products found!")
        
        return total_scanned, len(to_delete)


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Product Database Cleaning Tool")
    logger.info("="*60)
    
    validator = ProductValidator()
    total, deleted = validator.validate_and_clean()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL RESULTS:")
    logger.info(f"  Total products scanned: {total}")
    logger.info(f"  Invalid products deleted: {deleted}")
    logger.info(f"  Valid products remaining: {total - deleted}")
    logger.info(f"  Data quality: {((total - deleted) / total * 100):.1f}%")
    logger.info(f"{'='*60}")

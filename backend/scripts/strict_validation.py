"""
STRICT PRODUCT VALIDATION - Keep only REAL products that actually exist.
This will be very aggressive and remove most synthetic/generated products.
"""

import asyncio
import logging
from qdrant_client import QdrantClient
from collections import Counter
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealProductValidator:
    # Desktop CPU patterns that should NEVER appear in laptops
    DESKTOP_CPU_PATTERNS = [
        r'Ryzen \d+ \d{4}(?:X|G)?$',  # Ryzen 5 7600, Ryzen 9 7900X (no suffix = desktop)
        r'Core i\d+-\d{4,5}K',  # Intel K-series (desktop unlocked)
        r'Core i\d+-\d{4,5}F',  # Intel F-series (desktop no GPU)
        r'Core i\d+-\d{4,5}$',  # Intel without suffix (desktop)
    ]
    
    # Valid mobile CPU suffixes
    MOBILE_CPU_SUFFIXES = ['U', 'H', 'HS', 'HX', 'P', 'M', 'Y', 'G7', 'AI']
    
    # Generic/fake model patterns to reject
    FAKE_MODEL_PATTERNS = [
        r'^Model-\d+$',  # "Model-958"
        r'^Pad \d+$',  # "Pad 12"
        r'^Tab \d+$',  # "Tab 10"
        r'^MatePad \d+$',  # "MatePad 7" (not specific enough)
        r'^\d+ (Pro|Plus|Ultra|Max)? ?\d*GB$',  # "13 Pro 256GB" (no model name)
    ]
    
    # Real laptop product lines by manufacturer
    REAL_LAPTOP_LINES = {
        'lenovo': ['ThinkPad', 'IdeaPad', 'Legion', 'Yoga', 'ThinkBook'],
        'dell': ['XPS', 'Inspiron', 'Latitude', 'Precision', 'Alienware', 'Vostro'],
        'hp': ['Pavilion', 'Envy', 'Omen', 'EliteBook', 'ProBook', 'Spectre', 'ZBook'],
        'asus': ['ZenBook', 'VivoBook', 'ROG', 'TUF', 'ProArt', 'ExpertBook'],
        'acer': ['Aspire', 'Swift', 'Predator', 'Nitro', 'TravelMate', 'ConceptD'],
        'apple': ['MacBook Air', 'MacBook Pro'],
        'msi': ['Prestige', 'Modern', 'Creator', 'Katana', 'Cyborg', 'Stealth', 'Raider'],
        'microsoft': ['Surface Laptop', 'Surface Pro', 'Surface Book', 'Surface Go'],
    }
    
    # Real phone lines by manufacturer
    REAL_PHONE_LINES = {
        'apple': ['iPhone'],
        'samsung': ['Galaxy S', 'Galaxy A', 'Galaxy Z', 'Galaxy M', 'Galaxy Note'],
        'xiaomi': ['Redmi', 'Poco', 'Mi'],
        'huawei': ['P', 'Mate', 'nova'],
        'oppo': ['Find', 'Reno', 'A'],
        'vivo': ['V', 'Y', 'X'],
        'oneplus': ['OnePlus'],
        'nokia': ['Nokia'],
        'realme': ['realme'],
        'honor': ['Honor'],
    }
    
    def is_desktop_cpu(self, processor: str, category: str) -> bool:
        """Check if CPU is a desktop CPU (invalid for laptops)."""
        if 'laptop' not in category.lower() and 'ordinateur' not in category.lower():
            return False
        
        # Check for desktop CPU patterns
        for pattern in self.DESKTOP_CPU_PATTERNS:
            if re.search(pattern, processor):
                return True
        
        # Check for missing mobile suffix on Intel/AMD
        if 'Intel Core' in processor or 'Ryzen' in processor:
            has_mobile_suffix = any(processor.endswith(suffix) for suffix in self.MOBILE_CPU_SUFFIXES)
            has_mobile_marker = any(suffix in processor for suffix in self.MOBILE_CPU_SUFFIXES)
            
            if not has_mobile_suffix and not has_mobile_marker:
                # Likely desktop CPU
                if re.search(r'i\d+-\d{4,5}', processor) or re.search(r'Ryzen \d+ \d{4}', processor):
                    return True
        
        return False
    
    def is_fake_model(self, model: str, name: str) -> bool:
        """Check if model name is generic/fake."""
        for pattern in self.FAKE_MODEL_PATTERNS:
            if re.match(pattern, model, re.IGNORECASE):
                return True
            if re.match(pattern, name, re.IGNORECASE):
                return True
        
        return False
    
    def is_real_product_line(self, brand: str, model: str, name: str, category: str) -> bool:
        """Check if product belongs to a real manufacturer product line."""
        brand_lower = brand.lower()
        
        # Check laptops
        if 'laptop' in category.lower() or 'ordinateur' in category.lower():
            if brand_lower in self.REAL_LAPTOP_LINES:
                real_lines = self.REAL_LAPTOP_LINES[brand_lower]
                # Check if model/name contains any real product line
                for line in real_lines:
                    if line.lower() in model.lower() or line.lower() in name.lower():
                        return True
                return False  # No real product line found
        
        # Check smartphones
        if 'smartphone' in category.lower() or 'téléphone' in category.lower():
            if brand_lower in self.REAL_PHONE_LINES:
                real_lines = self.REAL_PHONE_LINES[brand_lower]
                for line in real_lines:
                    if line.lower() in model.lower() or line.lower() in name.lower():
                        return True
                return False
        
        # For other categories, be more lenient (TVs, accessories, tablets)
        return True
    
    def is_valid(self, product: dict) -> tuple[bool, str]:
        """Comprehensive validation - keep only REAL products."""
        brand = product.get('brand', '').lower()
        model = product.get('model', '')
        name = product.get('name', '')
        category = product.get('category', '')
        
        specs = product.get('specifications', {})
        processor = specs.get('processor', '')
        
        # Check 1: Fake/generic model names
        if self.is_fake_model(model, name):
            return False, f"Generic/fake model name: {model}"
        
        # Check 2: Desktop CPU in laptop
        if processor and self.is_desktop_cpu(processor, category):
            return False, f"Desktop CPU in laptop: {processor}"
        
        # Check 3: Real product line
        if not self.is_real_product_line(brand, model, name, category):
            return False, f"Not a real product line for {brand}"
        
        return True, ""


async def strict_validation():
    client = QdrantClient(url="http://localhost:6333")
    validator = RealProductValidator()
    
    print("=" * 80)
    print("STRICT REAL PRODUCT VALIDATION")
    print("=" * 80)
    print("⚠️  WARNING: This will remove most synthetic/generated products")
    print("Only keeping products that appear to be REAL products that actually exist")
    print("=" * 80)
    
    logger.info("\nScanning all products...")
    
    all_products = []
    invalid_products = []
    deletion_reasons = Counter()
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
            all_products.append(point)
            is_valid, reason = validator.is_valid(point.payload)
            
            if not is_valid:
                invalid_products.append(point.id)
                deletion_reasons[reason] += 1
        
        offset = result[1]
        if offset is None:
            break
        
        if len(all_products) % 5000 == 0:
            logger.info(f"Scanned {len(all_products):,} products, {len(invalid_products):,} will be removed...")
    
    logger.info(f"\nCompleted scanning {len(all_products):,} products\n")
    
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print(f"Total products scanned: {len(all_products):,}")
    print(f"Products to remove: {len(invalid_products):,} ({len(invalid_products)/len(all_products)*100:.1f}%)")
    print(f"Products to keep: {len(all_products) - len(invalid_products):,} ({(len(all_products) - len(invalid_products))/len(all_products)*100:.1f}%)")
    print("=" * 80)
    
    if deletion_reasons:
        print("\nRemoval reasons:")
        for reason, count in deletion_reasons.most_common(20):
            print(f"  - {reason}: {count:,}")
    
    print("\n" + "=" * 80)
    print(f"⚠️  This will DELETE {len(invalid_products):,} products permanently")
    print(f"✅ This will KEEP {len(all_products) - len(invalid_products):,} products")
    print("=" * 80)
    
    # Don't auto-delete - show what would happen
    print("\n❓ Do you want to proceed with deletion?")
    print("   Run with --execute flag to actually delete")
    
    return invalid_products, all_products


if __name__ == "__main__":
    import sys
    
    invalid, total = asyncio.run(strict_validation())
    
    if '--execute' in sys.argv:
        print("\n🔴 EXECUTING DELETION...")
        client = QdrantClient(url="http://localhost:6333")
        
        batch_size = 100
        for i in range(0, len(invalid), batch_size):
            batch = invalid[i:i + batch_size]
            client.delete(
                collection_name="products",
                points_selector=batch,
                wait=True
            )
            logger.info(f"Deleted batch {i//batch_size + 1}/{(len(invalid) + batch_size - 1)//batch_size}")
        
        print(f"\n✅ Successfully deleted {len(invalid):,} products")
        print(f"✅ Remaining: {len(total) - len(invalid):,} real products")
    else:
        print("\n💡 To execute deletion, run: python scripts/strict_validation.py --execute")

"""
Load Mytek.tn Scraped Products into Qdrant
Processes scraped products and uploads them with CLIP embeddings
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List
import uuid
import time

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.qdrant_client import QdrantManager
from core.config import settings
from core.embeddings import CLIPEmbedder
from qdrant_client.models import PointStruct

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Data file path
PRODUCTS_FILE = Path(__file__).parent.parent.parent / "data" / "mytek_products.json"

# Initialize services
qdrant_manager = QdrantManager()
embedder = CLIPEmbedder()
PRODUCTS_COLLECTION = settings.qdrant_collection_products


def load_json(filepath: Path) -> List[Dict]:
    """Load JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} products from {filepath.name}")
        return data
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return []


def process_product(product: Dict) -> Dict:
    """Convert Mytek scraped format to system format"""
    
    # Convert TND to USD (rate as of January 2026: approximately 1 TND = 0.32 USD)
    # TODO: Consider using a currency conversion API for real-time rates
    tnd_to_usd = 0.32
    price_usd = product.get('price_TND', 0) * tnd_to_usd
    original_price_usd = product.get('original_price_TND', 0) * tnd_to_usd
    
    # Extract specifications
    specs = product.get('specifications', {})
    
    # Build searchable text for embedding
    search_text = f"{product.get('name', '')} {product.get('brand', '')} {product.get('category', '')} "
    search_text += f"{product.get('subcategory', '')} {product.get('description', '')} "
    
    # Add specifications to search text
    for key, value in specs.items():
        search_text += f"{key} {value} "
    
    # Add features
    search_text += " ".join(product.get('features', []))
    
    # Create normalized product
    processed = {
        'product_id': product.get('id'),
        'name': product.get('name'),
        'price': round(price_usd, 2),
        'original_price': round(original_price_usd, 2),
        'category': product.get('category'),
        'subcategory': product.get('subcategory'),
        'brand': product.get('brand'),
        'model': product.get('model'),
        'description': product.get('description'),
        'rating': product.get('rating'),
        'num_reviews': product.get('number_of_reviews', 0),
        'availability': product.get('availability'),
        'condition': product.get('condition'),
        'stock_quantity': product.get('stock_quantity', 0),
        'discount_percentage': product.get('discount_percentage', 0),
        'color': product.get('color'),
        'colors_available': product.get('colors_available', []),
        'features': product.get('features', []),
        'images': product.get('images', []),
        'main_image': product.get('main_image'),
        'seller': product.get('seller'),
        'warranty': product.get('warranty'),
        'shipping': product.get('shipping'),
        'sku': product.get('sku'),
        'specifications': specs,
        'search_text': search_text,
        'created_at': product.get('created_at'),
        'updated_at': product.get('updated_at'),
        'source': 'mytek.tn',
        'source_url': product.get('url')
    }
    
    return processed


def upload_products_to_qdrant(products: List[Dict], batch_size: int = 50):
    """Upload products to Qdrant with CLIP embeddings"""
    
    total_products = len(products)
    logger.info(f"Uploading {total_products} products to Qdrant in batches of {batch_size}...")
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    # Process in batches
    for i in range(0, total_products, batch_size):
        batch = products[i:i + batch_size]
        points = []
        
        batch_start = time.time()
        
        for product in batch:
            try:
                # Generate CLIP embedding from search text
                embedding = embedder.encode_text(product['search_text'])
                
                # Get first embedding (returns 2D array, we want 1D)
                if len(embedding.shape) == 2:
                    embedding = embedding[0]
                
                # Convert numpy array to list
                embedding = embedding.tolist()
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={k: v for k, v in product.items() if k != 'search_text'}
                )
                points.append(point)
                
            except Exception as e:
                logger.error(f"Error processing product {product.get('product_id')}: {e}")
                failed += 1
                continue
        
        # Upload batch
        if points:
            try:
                qdrant_manager.client.upsert(
                    collection_name=PRODUCTS_COLLECTION,
                    points=points
                )
                successful += len(points)
                
                batch_time = time.time() - batch_start
                progress = (i + len(batch)) / total_products * 100
                
                logger.info(
                    f"Progress: {progress:.1f}% | "
                    f"Batch {i//batch_size + 1}/{(total_products-1)//batch_size + 1} | "
                    f"{len(points)} products | "
                    f"{batch_time:.2f}s"
                )
                
            except Exception as e:
                logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                failed += len(points)
                continue
    
    total_time = time.time() - start_time
    
    logger.info(f"✅ Upload complete!")
    logger.info(f"   Successful: {successful}")
    logger.info(f"   Failed: {failed}")
    logger.info(f"   Total time: {total_time:.2f}s")
    if total_products > 0:
        logger.info(f"   Average: {total_time/total_products:.3f}s per product")
    
    return successful, failed


def main():
    """Main data loading pipeline"""
    
    print("=" * 80)
    print("🔄 LOADING MYTEK.TN PRODUCTS INTO QDRANT")
    print("=" * 80)
    print()
    
    # Check if file exists
    if not PRODUCTS_FILE.exists():
        print(f"❌ Error: Product file not found: {PRODUCTS_FILE}")
        print(f"   Please run the scraper first:")
        print(f"   From repository root: python backend/scripts/scrape_mytek.py")
        print(f"   From backend directory: python scripts/scrape_mytek.py")
        return
    
    # Step 1: Load JSON file
    print("📂 Step 1: Loading products JSON file...")
    raw_products = load_json(PRODUCTS_FILE)
    
    if not raw_products:
        print("❌ Error: Could not load products data")
        return
    
    print(f"✅ Loaded {len(raw_products)} products")
    print()
    
    # Step 2: Process products
    print("🔄 Step 2: Processing products...")
    processed_products = []
    for i, product in enumerate(raw_products):
        try:
            processed = process_product(product)
            processed_products.append(processed)
            
            if (i + 1) % 100 == 0:
                print(f"   Processed {i + 1}/{len(raw_products)} products...")
        except Exception as e:
            logger.error(f"Error processing product {i}: {e}")
    
    print(f"✅ Processed {len(processed_products)} products")
    print()
    
    # Step 3: Upload to Qdrant
    print("📤 Step 3: Uploading to Qdrant...")
    successful, failed = upload_products_to_qdrant(processed_products)
    
    print()
    print("=" * 80)
    print("✅ LOADING COMPLETE!")
    print(f"   Total processed: {len(processed_products)}")
    print(f"   Successfully uploaded: {successful}")
    print(f"   Failed: {failed}")
    print("=" * 80)


if __name__ == '__main__':
    main()

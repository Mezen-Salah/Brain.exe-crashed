"""
Convert all product prices from USD back to TND
Since we loaded with 0.32 conversion, we multiply by 3.125 (1/0.32) to get back to TND
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

def convert_prices_to_tnd():
    """Convert all product prices from USD to TND"""
    
    # Conversion rate: USD to TND (reverse of 0.32)
    usd_to_tnd = 3.125  # 1 / 0.32
    
    collection_name = settings.qdrant_collection_products
    
    # Get all products
    logger.info("Fetching all products...")
    offset = None
    batch_size = 100
    total_updated = 0
    
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
            
        # Update each product
        for point in result:
            point_id = point.id
            payload = point.payload
            
            # Convert prices
            old_price = payload.get('price', 0)
            old_original_price = payload.get('original_price', 0)
            
            new_price = round(old_price * usd_to_tnd, 2)
            new_original_price = round(old_original_price * usd_to_tnd, 2)
            
            # Update payload
            payload['price'] = new_price
            payload['original_price'] = new_original_price
            
            # Update in Qdrant
            qdrant_manager.client.set_payload(
                collection_name=collection_name,
                points=[point_id],
                payload=payload
            )
            
            total_updated += 1
            
            if total_updated % 1000 == 0:
                logger.info(f"Updated {total_updated} products...")
        
        # Check if there are more products
        if next_offset is None:
            break
        offset = next_offset
    
    logger.info(f"✅ Successfully converted {total_updated} products from USD to TND")
    logger.info(f"Conversion rate used: 1 USD = {usd_to_tnd} TND")

if __name__ == "__main__":
    logger.info("Starting USD to TND conversion...")
    convert_prices_to_tnd()
    logger.info("Conversion complete!")

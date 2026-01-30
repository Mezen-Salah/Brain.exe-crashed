"""
Load data from 'data 2.0' folder into Qdrant
Products, Users, Transactions with 512-dim CLIP embeddings
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List
import time

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.qdrant_client import QdrantManager
from core.config import settings
from core.embeddings import CLIPEmbedder
from qdrant_client.models import PointStruct

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Data folder
DATA_FOLDER = Path("C:/Users/mezen/OneDrive/Desktop/data 2.0")

# Initialize services
qdrant_manager = QdrantManager()
embedder = CLIPEmbedder()


def load_products():
    """Load products from data 2.0"""
    logger.info("=" * 80)
    logger.info("LOADING PRODUCTS")
    logger.info("=" * 80)
    
    # Load JSON
    products_file = DATA_FOLDER / "products.json"
    with open(products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    products = data['products']
    logger.info(f"Loaded {len(products)} products")
    
    # Process in batches
    batch_size = 50
    total = len(products)
    points = []
    
    for i, product in enumerate(products):
        # Generate embedding from name + description
        text = f"{product['name']} {product['description']}"
        embedding = embedder.encode_query(text)
        
        # Create point
        point = PointStruct(
            id=hash(product['product_id']) & 0x7FFFFFFF,
            vector=embedding,
            payload={
                'product_id': product['product_id'],
                'name': product['name'],
                'description': product['description'],
                'price': float(product['price']),
                'category': product['category'],
                'rating': float(product.get('rating', 0)),
                'num_reviews': int(product.get('reviews_count', 0)),
                'in_stock': product.get('in_stock', True),
                'financing_available': product.get('financing_available', False),
                'financing_terms': product.get('financing_terms', ''),
                'cluster_id': product.get('cluster_id', 0),
                'image_url': product.get('image_url', ''),
                'brand': product.get('brand', ''),
                'stock_quantity': product.get('stock_quantity', 0)
            }
        )
        points.append(point)
        
        # Upload in batches
        if len(points) >= batch_size or i == total - 1:
            qdrant_manager.client.upsert(
                collection_name=settings.qdrant_collection_products,
                points=points
            )
            logger.info(f"Uploaded batch {i+1}/{total} ({len(points)} products)")
            points = []
        
        # Progress
        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
    
    logger.info(f"✅ Successfully uploaded {total} products")


def load_users():
    """Load users from data 2.0"""
    logger.info("=" * 80)
    logger.info("LOADING USERS")
    logger.info("=" * 80)
    
    # Load JSON
    users_file = DATA_FOLDER / "users.json"
    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    users = data['users']
    logger.info(f"Loaded {len(users)} users")
    
    # Process in batches
    batch_size = 100
    total = len(users)
    points = []
    
    for i, user in enumerate(users):
        # Generate embedding from user preferences
        text = f"{user.get('preferred_categories', '')} {user.get('risk_tolerance', '')}"
        embedding = embedder.encode_query(text)
        
        # Create point
        point = PointStruct(
            id=hash(user['user_id']) & 0x7FFFFFFF,
            vector=embedding,
            payload={
                'user_id': user['user_id'],
                'monthly_income': float(user.get('monthly_income', 0)),
                'monthly_expenses': float(user.get('monthly_expenses', 0)),
                'savings': float(user.get('savings', 0)),
                'credit_score': int(user.get('credit_score', 650)),
                'risk_tolerance': user.get('risk_tolerance', 'medium'),
                'preferred_categories': user.get('preferred_categories', []),
                'purchase_history': user.get('purchase_history', [])
            }
        )
        points.append(point)
        
        # Upload in batches
        if len(points) >= batch_size or i == total - 1:
            qdrant_manager.client.upsert(
                collection_name=settings.qdrant_collection_users,
                points=points
            )
            logger.info(f"Uploaded batch {i+1}/{total} ({len(points)} users)")
            points = []
    
    logger.info(f"✅ Successfully uploaded {total} users")


def load_transactions():
    """Load transactions from data 2.0"""
    logger.info("=" * 80)
    logger.info("LOADING TRANSACTIONS")
    logger.info("=" * 80)
    
    # Load JSON
    transactions_file = DATA_FOLDER / "transactions.json"
    with open(transactions_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    transactions = data['transactions']
    logger.info(f"Loaded {len(transactions)} transactions")
    
    # Process in batches
    batch_size = 100
    total = len(transactions)
    points = []
    
    for i, txn in enumerate(transactions):
        # Generate embedding from action + product
        text = f"{txn['user_id']} {txn['action']} {txn.get('product_id', '')}"
        embedding = embedder.encode_query(text)
        
        # Create point
        point = PointStruct(
            id=hash(txn['transaction_id']) & 0x7FFFFFFF,
            vector=embedding,
            payload={
                'transaction_id': txn['transaction_id'],
                'user_id': txn['user_id'],
                'product_id': txn.get('product_id', ''),
                'action': txn['action'],
                'timestamp': txn['timestamp'],
                'rating': txn.get('rating'),
                'additional_data': txn.get('additional_data', {})
            }
        )
        points.append(point)
        
        # Upload in batches
        if len(points) >= batch_size or i == total - 1:
            qdrant_manager.client.upsert(
                collection_name=settings.qdrant_collection_transactions,
                points=points
            )
            logger.info(f"Uploaded batch {i+1}/{total} ({len(points)} transactions)")
            points = []
    
    logger.info(f"✅ Successfully uploaded {total} transactions")


def load_financial_kb():
    """Load financial knowledge base"""
    logger.info("=" * 80)
    logger.info("LOADING FINANCIAL KNOWLEDGE BASE")
    logger.info("=" * 80)
    
    # Load JSON
    kb_file = DATA_FOLDER / "financial_kb.json"
    with open(kb_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rules = data['rules']
    logger.info(f"Loaded {len(rules)} financial rules")
    
    points = []
    for i, rule in enumerate(rules):
        # Generate embedding from rule text
        embedding = embedder.encode_query(rule['text'])
        
        # Create point
        point = PointStruct(
            id=hash(rule['rule_id']) & 0x7FFFFFFF,
            vector=embedding,
            payload={
                'chunk_id': rule['rule_id'],
                'text': rule['text'],
                'category': rule.get('category', 'general'),
                'source': rule.get('source', 'system')
            }
        )
        points.append(point)
    
    # Upload all at once (small dataset)
    qdrant_manager.client.upsert(
        collection_name=settings.qdrant_collection_financial_kb,
        points=points
    )
    
    logger.info(f"✅ Successfully uploaded {len(rules)} financial rules")


if __name__ == "__main__":
    start_time = time.time()
    
    print()
    print("=" * 80)
    print("🚀 LOADING ALL DATA FROM 'data 2.0' FOLDER")
    print("=" * 80)
    print()
    
    # Load all datasets
    load_products()
    print()
    
    load_users()
    print()
    
    load_transactions()
    print()
    
    load_financial_kb()
    print()
    
    elapsed = time.time() - start_time
    
    print("=" * 80)
    print("✅ ALL DATA LOADED SUCCESSFULLY")
    print("=" * 80)
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print()
    
    # Verify
    print("📊 Final Counts:")
    for coll in ['products', 'users', 'transactions', 'financial_kb']:
        count = qdrant_manager.count_points(coll)
        print(f"   • {coll}: {count} items")

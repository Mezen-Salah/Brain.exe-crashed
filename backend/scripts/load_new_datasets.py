"""
Load all new datasets into Qdrant collections.
"""

import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Initialize clients
client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

DATA_PATH = r"C:\Users\mezen\OneDrive\Desktop\data 2.0"

print("=" * 80)
print("LOADING NEW DATASETS INTO QDRANT")
print("=" * 80)

# ============================================================================
# 1. LOAD PRODUCTS
# ============================================================================
print("\n📦 Loading products...")
with open(f"{DATA_PATH}\\products.json", "r", encoding="utf-8") as f:
    products_data = json.load(f)

products = products_data.get('products', [])
print(f"   Found {len(products):,} products")

# Process products in batches
batch_size = 100
products_points = []

for i, product in enumerate(tqdm(products, desc="Processing products")):
    # Create search text for embedding
    search_text = f"{product.get('name', '')} {product.get('brand', '')} {product.get('category', '')} {product.get('description', '')}"
    
    # Generate embedding
    embedding = model.encode(search_text).tolist()
    
    # Create point
    point = PointStruct(
        id=product.get('product_id', f"prod_{i}"),
        vector=embedding,
        payload=product
    )
    products_points.append(point)
    
    # Upload batch
    if len(products_points) >= batch_size:
        client.upsert(collection_name="products", points=products_points, wait=True)
        products_points = []

# Upload remaining
if products_points:
    client.upsert(collection_name="products", points=products_points, wait=True)

print(f"   ✅ Loaded {len(products):,} products")

# ============================================================================
# 2. LOAD USERS
# ============================================================================
print("\n👤 Loading users...")
with open(f"{DATA_PATH}\\users.json", "r", encoding="utf-8") as f:
    users_data = json.load(f)

users = users_data.get('users', [])
print(f"   Found {len(users):,} users")

# Process users in batches
users_points = []

for i, user in enumerate(tqdm(users, desc="Processing users")):
    # Create profile text for embedding
    profile_text = f"{user.get('name', '')} {user.get('preferences', {}).get('categories', [])} "
    profile_text += f"{user.get('preferences', {}).get('brands', [])} {user.get('location', '')}"
    
    # Generate embedding
    embedding = model.encode(profile_text).tolist()
    
    # Create point
    point = PointStruct(
        id=user.get('user_id', f"user_{i}"),
        vector=embedding,
        payload=user
    )
    users_points.append(point)
    
    # Upload batch
    if len(users_points) >= batch_size:
        client.upsert(collection_name="users", points=users_points, wait=True)
        users_points = []

# Upload remaining
if users_points:
    client.upsert(collection_name="users", points=users_points, wait=True)

print(f"   ✅ Loaded {len(users):,} users")

# ============================================================================
# 3. LOAD FINANCIAL KB
# ============================================================================
print("\n💰 Loading financial knowledge base...")
with open(f"{DATA_PATH}\\financial_kb.json", "r", encoding="utf-8") as f:
    kb_data = json.load(f)

kb_entries = kb_data.get('rules', [])
print(f"   Found {len(kb_entries):,} KB entries")

# Process KB entries
kb_points = []

for i, entry in enumerate(tqdm(kb_entries, desc="Processing KB")):
    # Create text for embedding
    kb_text = f"{entry.get('title', '')} {entry.get('content', '')} {entry.get('category', '')}"
    
    # Generate embedding
    embedding = model.encode(kb_text).tolist()
    
    # Create point
    point = PointStruct(
        id=entry.get('rule_id', f"kb_{i}"),
        vector=embedding,
        payload=entry
    )
    kb_points.append(point)

# Upload all KB entries
if kb_points:
    client.upsert(collection_name="financial_kb", points=kb_points, wait=True)

print(f"   ✅ Loaded {len(kb_entries):,} KB entries")

# ============================================================================
# 4. LOAD TRANSACTIONS
# ============================================================================
print("\n💳 Loading transactions...")
with open(f"{DATA_PATH}\\transactions.json", "r", encoding="utf-8") as f:
    transactions_data = json.load(f)

transactions = transactions_data.get('transactions', [])
print(f"   Found {len(transactions):,} transactions")

# Process transactions in batches
transactions_points = []

for i, transaction in enumerate(tqdm(transactions, desc="Processing transactions")):
    # Create text for embedding
    trans_text = f"{transaction.get('user_id', '')} {transaction.get('product_id', '')} "
    trans_text += f"{transaction.get('category', '')} {transaction.get('amount', '')}"
    
    # Generate embedding
    embedding = model.encode(trans_text).tolist()
    
    # Create point
    point = PointStruct(
        id=transaction.get('transaction_id', f"trans_{i}"),
        vector=embedding,
        payload=transaction
    )
    transactions_points.append(point)
    
    # Upload batch
    if len(transactions_points) >= batch_size:
        client.upsert(collection_name="transactions", points=transactions_points, wait=True)
        transactions_points = []

# Upload remaining
if transactions_points:
    client.upsert(collection_name="transactions", points=transactions_points, wait=True)

print(f"   ✅ Loaded {len(transactions):,} transactions")

# ============================================================================
# VERIFICATION
# ============================================================================
print("\n" + "=" * 80)
print("📊 VERIFICATION - Current collection counts:")
print("=" * 80)

collections = ["products", "users", "financial_kb", "transactions"]
for collection_name in collections:
    info = client.get_collection(collection_name)
    print(f"   {collection_name:20s}: {info.points_count:,} items")

print("\n" + "=" * 80)
print("✅ ALL DATASETS LOADED SUCCESSFULLY!")
print("=" * 80)

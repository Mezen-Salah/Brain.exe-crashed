"""
Load datasets with progress tracking and error handling.
"""

import json
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
import sys
import hashlib

def str_to_int_id(s):
    """Convert string ID to integer ID using hash"""
    return int(hashlib.md5(s.encode()).hexdigest()[:15], 16)

# Initialize
client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
DATA_PATH = r"C:\Users\mezen\OneDrive\Desktop\data 2.0"

print("=" * 80)
print("LOADING DATASETS")
print("=" * 80)

try:
    # PRODUCTS
    print("\n[1/4] Products...", end=" ", flush=True)
    with open(f"{DATA_PATH}\\products.json", "r", encoding="utf-8") as f:
        products = json.load(f).get('products', [])
    
    batch = []
    for i, p in enumerate(products):
        text = f"{p.get('name', '')} {p.get('description', '')} {p.get('category', '')}"
        embedding = model.encode(text).tolist()
        prod_id = str_to_int_id(p.get('product_id', f"p{i}"))
        batch.append(PointStruct(id=prod_id, vector=embedding, payload=p))
        
        if len(batch) >= 100:
            client.upsert(collection_name="products", points=batch, wait=True)
            batch = []
            print(f"\r[1/4] Products... {i+1}/{len(products)}", end="", flush=True)
    
    if batch:
        client.upsert(collection_name="products", points=batch, wait=True)
    
    print(f"\r[1/4] Products... ✅ {len(products)} loaded")
    
    # USERS
    print("[2/4] Users...", end=" ", flush=True)
    with open(f"{DATA_PATH}\\users.json", "r", encoding="utf-8") as f:
        users = json.load(f).get('users', [])
    
    batch = []
    for i, u in enumerate(users):
        profile = u.get('profile', {})
        text = f"{profile.get('name', '')} {profile.get('location', '')}"
        embedding = model.encode(text).tolist()
        user_id = str_to_int_id(u.get('user_id', f"u{i}"))
        batch.append(PointStruct(id=user_id, vector=embedding, payload=u))
        
        if len(batch) >= 100:
            client.upsert(collection_name="users", points=batch, wait=True)
            batch = []
            print(f"\r[2/4] Users... {i+1}/{len(users)}", end="", flush=True)
    
    if batch:
        client.upsert(collection_name="users", points=batch, wait=True)
    
    print(f"\r[2/4] Users... ✅ {len(users)} loaded")
    
    # FINANCIAL KB
    print("[3/4] Financial KB...", end=" ", flush=True)
    with open(f"{DATA_PATH}\\financial_kb.json", "r", encoding="utf-8") as f:
        rules = json.load(f).get('rules', [])
    
    batch = []
    for i, r in enumerate(rules):
        text = f"{r.get('title', '')} {r.get('content', '')} {r.get('category', '')}"
        embedding = model.encode(text).tolist()
        rule_id = str_to_int_id(r.get('rule_id', f"r{i}"))
        batch.append(PointStruct(id=rule_id, vector=embedding, payload=r))
    
    if batch:
        client.upsert(collection_name="financial_kb", points=batch, wait=True)
    
    print(f"\r[3/4] Financial KB... ✅ {len(rules)} loaded")
    
    # TRANSACTIONS
    print("[4/4] Transactions...", end=" ", flush=True)
    with open(f"{DATA_PATH}\\transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f).get('transactions', [])
    
    batch = []
    for i, t in enumerate(transactions):
        text = f"{t.get('user_id', '')} {t.get('product_id', '')} {t.get('action', '')}"
        embedding = model.encode(text).tolist()
        trans_id = str_to_int_id(t.get('transaction_id', f"t{i}"))
        batch.append(PointStruct(id=trans_id, vector=embedding, payload=t))
        
        if len(batch) >= 100:
            client.upsert(collection_name="transactions", points=batch, wait=True)
            batch = []
            print(f"\r[4/4] Transactions... {i+1}/{len(transactions)}", end="", flush=True)
    
    if batch:
        client.upsert(collection_name="transactions", points=batch, wait=True)
    
    print(f"\r[4/4] Transactions... ✅ {len(transactions)} loaded")
    
    # VERIFY
    print("\n" + "=" * 80)
    print("FINAL COUNTS:")
    for col in ['products', 'users', 'financial_kb', 'transactions']:
        count = client.get_collection(col).points_count
        print(f"  {col:20s}: {count:,}")
    print("=" * 80)
    print("✅ ALL DATASETS LOADED!")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

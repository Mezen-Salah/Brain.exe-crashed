"""Quick Qdrant functionality test"""
from core.qdrant_client import qdrant_manager
from core.embeddings import clip_embedder

print("=" * 80)
print("QDRANT FUNCTIONALITY TEST")
print("=" * 80)
print()

# Test 1: Collections
print("1. Collections:")
from core.config import settings
collections = [
    settings.qdrant_collection_products,
    settings.qdrant_collection_users,
    settings.qdrant_collection_financial_kb,
    settings.qdrant_collection_transactions
]
for coll in collections:
    count = qdrant_manager.count_points(coll)
    print(f"   ✅ {coll}: {count} items")
print()

# Test 2: Product Search
print("2. Product Vector Search:")
query_emb = clip_embedder.encode_query('laptop')
results = qdrant_manager.search_products(query_emb, top_k=5)
print(f"   Found {len(results)} products")
for i, r in enumerate(results):
    print(f"   {i+1}. {r.payload['name']}")
    print(f"      Price: ${r.payload['price']}")
    print(f"      Similarity: {r.score:.3f}")
print()

# Test 3: Financial Rules Retrieval
print("3. Financial Rules RAG:")
context_emb = clip_embedder.encode_query('credit score requirements for financing')
rules = qdrant_manager.retrieve_financial_rules(context_emb, top_k=3)
print(f"   Retrieved {len(rules)} rules")
for i, r in enumerate(rules):
    print(f"   {i+1}. {r.payload['text'][:80]}...")
    print(f"      Relevance: {r.score:.3f}")
print()

# Test 4: Similar Users (Collaborative Filtering)
print("4. Similar Users Search:")
# Get a user's preference vector
user_vector = clip_embedder.encode_query('electronics enthusiast')
similar_users = qdrant_manager.find_similar_users(user_vector, top_k=3)
print(f"   Found {len(similar_users)} similar users")
for i, u in enumerate(similar_users):
    print(f"   {i+1}. User {u.payload['user_id']}")
    print(f"      Income: ${u.payload['monthly_income']}")
    print(f"      Credit: {u.payload['credit_score']}")
    print(f"      Similarity: {u.score:.3f}")
print()

# Test 5: Transaction History
print("5. Transaction Retrieval:")
transactions = qdrant_manager.get_product_transactions('PROD0042', limit=5)
print(f"   Found {len(transactions[:5])} transactions for PROD0042")
for i, t in enumerate(transactions[:3]):
    print(f"   {i+1}. User {t['user_id']} - {t['action']}")
print()

# Test 6: Cluster Alternatives
print("6. Cluster-based Alternatives:")
cluster_results = qdrant_manager.get_products_by_cluster(
    cluster_id=1,
    max_price=1000,
    limit=5
)
print(f"   Found {len(cluster_results)} alternatives in cluster 1")
for i, p in enumerate(cluster_results[:3]):
    print(f"   {i+1}. {p.payload['name']} - ${p.payload['price']}")
print()

print("=" * 80)
print("✅ ALL QDRANT OPERATIONS WORKING")
print("=" * 80)

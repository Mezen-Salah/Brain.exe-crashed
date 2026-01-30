"""Test search directly"""
from core.embeddings import clip_embedder
from core.qdrant_client import qdrant_manager

# Generate embedding
query = "laptop"
embedding = clip_embedder.encode_query(query)

print(f"Query: {query}")
print(f"Embedding dimension: {len(embedding)}")

# Search with no threshold
results = qdrant_manager.client.search(
    collection_name="products",
    query_vector=embedding,
    limit=10,
    score_threshold=None  # No threshold
)

print(f"\nFound {len(results)} results")
for i, result in enumerate(results[:5], 1):
    print(f"\n{i}. Score: {result.score:.4f}")
    print(f"   Name: {result.payload.get('name', 'N/A')}")
    print(f"   Category: {result.payload.get('category', 'N/A')}")
    print(f"   Price: ${result.payload.get('price', 0):.2f}")

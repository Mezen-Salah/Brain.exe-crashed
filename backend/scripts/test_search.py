"""
Test search to debug why 0 results.
"""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Check collection info
info = client.get_collection("products")
print(f"Collection: products")
print(f"  Points: {info.points_count}")
print(f"  Vector size: {info.config.params.vectors.size}")

# Get a sample product
scroll_result = client.scroll(
    collection_name="products",
    limit=1,
    with_payload=True,
    with_vectors=False
)

if scroll_result[0]:
    sample = scroll_result[0][0].payload
    print(f"\nSample product:")
    print(f"  Name: {sample.get('name')}")
    print(f"  Category: {sample.get('category')}")
    print(f"  Price: {sample.get('price')}")
    print(f"  Keys: {list(sample.keys())}")

# Try a search
query = "laptop"
print(f"\nSearching for: '{query}'")
embedding = model.encode(query).tolist()
print(f"Embedding dimension: {len(embedding)}")

results = client.search(
    collection_name="products",
    query_vector=embedding,
    limit=5,
    score_threshold=0.0
)

print(f"\nSearch results: {len(results)}")
for i, result in enumerate(results[:3]):
    print(f"{i+1}. Score: {result.score:.3f}")
    print(f"   Name: {result.payload.get('name')}")
    print(f"   Category: {result.payload.get('category')}")

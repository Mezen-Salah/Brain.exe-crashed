from core.embeddings import CLIPEmbedder
from qdrant_client import QdrantClient

# Initialize
embedder = CLIPEmbedder()
client = QdrantClient(host='localhost', port=6333)

# Generate embedding for "laptop"
query_embedding = embedder.encode_query("laptop")
print(f"Query embedding dimension: {len(query_embedding)}")
print(f"First 5 values: {query_embedding[:5]}")

# Search Qdrant
results = client.search(
    collection_name='products',
    query_vector=query_embedding,
    limit=5,
    score_threshold=0.0  # No threshold to see all results
)

print(f"\nSearch results: {len(results)}")
for i, result in enumerate(results[:3]):
    print(f"\n{i+1}. Score: {result.score:.4f}")
    print(f"   ID: {result.id}")
    print(f"   Payload keys: {list(result.payload.keys())}")
    if 'name' in result.payload:
        print(f"   Name: {result.payload['name']}")

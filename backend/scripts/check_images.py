from qdrant_client import QdrantClient

c = QdrantClient('http://localhost:6333')
r = c.scroll('products', limit=5, with_payload=True)

print('CURRENT IMAGE URL EXAMPLES:\n')
print('=' * 80)

for p in r[0]:
    payload = p.payload
    print(f"\nProduct: {payload.get('name')}")
    print(f"Brand: {payload.get('brand')}")
    print(f"Category: {payload.get('category')}")
    print(f"Main Image: {payload.get('main_image')}")
    print(f"Images: {payload.get('images')}")
    print('=' * 80)

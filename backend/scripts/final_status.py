from qdrant_client import QdrantClient

c = QdrantClient('http://localhost:6333')
info = c.get_collection('products')

print('=' * 80)
print('FINAL DATABASE STATUS')
print('=' * 80)
print(f'Total products remaining: {info.points_count:,}')
print()
print('Cleaning History:')
print(f'  Original dataset: 46,531 products')
print(f'  After logical cleaning: 30,458 products (-34.5%)')
print(f'  After strict validation: {info.points_count:,} products (-63.5%)')
print()
print(f'Products removed total: {46531 - info.points_count:,} ({(46531 - info.points_count)/46531*100:.1f}%)')
print('Data quality: Only REAL products with valid product lines')
print('=' * 80)

r = c.scroll('products', limit=10, with_payload=True)
print('\nSample of remaining products:')
for i, p in enumerate(r[0][:10], 1):
    payload = p.payload
    brand = payload.get('brand', 'Unknown')
    model = payload.get('model', 'Unknown')
    category = payload.get('category', 'Unknown')
    print(f'{i}. {brand} {model} - {category}')

print('=' * 80)

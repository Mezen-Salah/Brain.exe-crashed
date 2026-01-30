import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.qdrant_client import qdrant_manager
from core.embeddings import clip_embedder
from core.config import settings
from qdrant_client.models import PointStruct
import json

# Load financial KB
with open('C:/Users/mezen/OneDrive/Desktop/data 2.0/financial_kb.json', 'r') as f:
    data = json.load(f)

rules = data['rules']
print(f'Loading {len(rules)} financial rules...')

points = []
for rule in rules:
    # Use content field and title
    text = f"{rule['title']} {rule['content']}"
    embedding = clip_embedder.encode_query(text)
    point = PointStruct(
        id=hash(rule['rule_id']) & 0x7FFFFFFF,
        vector=embedding,
        payload={
            'chunk_id': rule['rule_id'],
            'text': rule['content'],
            'category': rule.get('category', 'general'),
            'source': 'financial_kb',
            'title': rule['title'],
            'tags': rule.get('tags', [])
        }
    )
    points.append(point)

qdrant_manager.client.upsert(
    collection_name=settings.qdrant_collection_financial_kb,
    points=points
)

print(f'✅ Successfully uploaded {len(rules)} financial rules')
print(f'Total in collection: {qdrant_manager.count_points(settings.qdrant_collection_financial_kb)}')

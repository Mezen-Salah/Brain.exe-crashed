import requests
import json

response = requests.post(
    'http://localhost:8000/api/search',
    json={'query': 'laptop'},
    timeout=10
)

print(f'Status: {response.status_code}')
print(f'Response:')
print(json.dumps(response.json(), indent=2)[:1000])

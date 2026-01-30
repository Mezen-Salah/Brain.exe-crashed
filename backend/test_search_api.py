import requests
import json

try:
    response = requests.post(
        'http://localhost:8000/api/search',
        json={'query': 'laptop'},
        timeout=10
    )
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        products = result.get('products', [])
        print(f'Products found: {len(products)}')
        
        if products:
            print(f'\nFirst product:')
            print(f"  Name: {products[0]['name']}")
            print(f"  Score: {products[0].get('score', 'N/A')}")
            print(f"  Price: {products[0].get('price', 'N/A')}")
    else:
        print(f'Error: {response.text}')
        
except Exception as e:
    print(f'Error: {e}')

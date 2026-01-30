"""
Check structure of JSON files.
"""

import json

DATA_PATH = r"C:\Users\mezen\OneDrive\Desktop\data 2.0"

files = ['products.json', 'users.json', 'financial_kb.json', 'transactions.json']

for filename in files:
    print(f"\n{'='*60}")
    print(f"FILE: {filename}")
    print('='*60)
    
    with open(f"{DATA_PATH}\\{filename}", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Type: {type(data)}")
    
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for key in data.keys():
            if isinstance(data[key], list):
                print(f"  {key}: {len(data[key])} items")
                if len(data[key]) > 0:
                    print(f"  First item keys: {list(data[key][0].keys())[:10]}")
    elif isinstance(data, list):
        print(f"List length: {len(data)}")
        if len(data) > 0:
            print(f"First item keys: {list(data[0].keys())[:10]}")

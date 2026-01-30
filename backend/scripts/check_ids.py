import json

with open(r"C:\Users\mezen\OneDrive\Desktop\data 2.0\products.json", encoding="utf-8") as f:
    products = json.load(f)['products']

print("First 3 product IDs:")
for p in products[:3]:
    print(f"  {p['product_id']} (type: {type(p['product_id']).__name__})")

"""
Quick MCP Tools Test
Tests a few MCP tools to verify they work correctly
"""
from mcp_server import (
    qdrant_search_products,
    calculate_affordability,
    redis_get_thompson_params
)

print("=" * 80)
print("MCP TOOLS INTEGRATION TEST")
print("=" * 80)

# Test 1: Product Search
print("\n[TEST 1] qdrant_search_products")
print("-" * 80)
try:
    result = qdrant_search_products.invoke({
        'query': 'laptop',
        'budget': 1500,
        'top_k': 3
    })
    
    if result['success']:
        print(f"✅ SUCCESS")
        print(f"   Query: {result['query']}")
        print(f"   Total Results: {result['total_results']}")
        if result['products']:
            p = result['products'][0]
            print(f"   Top Product: {p['name'][:50]}")
            print(f"   Price: ${p['price']}")
            print(f"   Similarity: {p['similarity_score']:.3f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: Affordability Calculation
print("\n[TEST 2] calculate_affordability")
print("-" * 80)
try:
    result = calculate_affordability.invoke({
        'price': 999.99,
        'monthly_income': 3000,
        'monthly_expenses': 1800,
        'savings': 5000,
        'credit_score': 720
    })
    
    if result['success']:
        print(f"✅ SUCCESS")
        print(f"   Affordable: {result['is_affordable']}")
        print(f"   Affordability Score: {result['affordability_score']:.1f}")
        print(f"   Cash Score: {result['cash_score']:.1f}")
        print(f"   Credit Score: {result['credit_score']:.1f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 3: Thompson Sampling Parameters
print("\n[TEST 3] redis_get_thompson_params")
print("-" * 80)
try:
    result = redis_get_thompson_params.invoke({
        'product_id': 'PROD0001'
    })
    
    if result['success']:
        print(f"✅ SUCCESS")
        print(f"   Product ID: {result['product_id']}")
        print(f"   Alpha (successes): {result['alpha']}")
        print(f"   Beta (failures): {result['beta']}")
        print(f"   Ratio: {result['ratio']:.3f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "=" * 80)
print("MCP TOOLS TEST COMPLETE")
print("=" * 80)

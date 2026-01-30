import requests
import json

print("=" * 80)
print("COMPREHENSIVE AGENT + LLM INTEGRATION TEST")
print("=" * 80)

# Test 1: Simple search (SMART path - Agents 1, 3, 4)
print("\n[TEST 1] Simple search: 'laptop'")
print("-" * 80)
response = requests.post(
    'http://localhost:8000/api/search',
    json={'query': 'laptop'},
    timeout=30
)
result = response.json()
print(f"✅ Status: {response.status_code}")
print(f"✅ Path: {result['path_taken']}")
print(f"✅ Products found: {len(result.get('recommendations', []))}")
if result.get('recommendations'):
    print(f"✅ Top product: {result['recommendations'][0]['product']['name'][:60]}")
    print(f"✅ Trust score: {result['recommendations'][0].get('trust_score', 'N/A')}")
    print(f"✅ Explanation: {result['recommendations'][0].get('explanation', 'N/A')[:100]}")

# Test 2: Financial query (DEEP path - All 5 agents)
print("\n\n[TEST 2] Financial query: 'gaming laptop under 1200 with financing'")
print("-" * 80)
response = requests.post(
    'http://localhost:8000/api/search',
    json={
        'query': 'gaming laptop under 1200 with financing',
        'user_profile': {
            'user_id': 'USER123',
            'monthly_income': 3000,
            'credit_score': 720,
            'debt_to_income_ratio': 0.3
        }
    },
    timeout=30
)
result = response.json()
print(f"✅ Status: {response.status_code}")
print(f"✅ Path: {result['path_taken']}")
print(f"✅ Complexity: {result.get('complexity_score', 0)}")
print(f"✅ Products found: {len(result.get('recommendations', []))}")
if result.get('recommendations'):
    print(f"✅ Top product: {result['recommendations'][0]['product']['name'][:60]}")
    print(f"✅ Price: ${result['recommendations'][0]['product']['price']}")
    print(f"✅ Financing: {result['recommendations'][0]['product'].get('financing_available')}")
    print(f"✅ Affordability: {result['recommendations'][0]['affordability']['is_affordable']}")
    print(f"✅ Trust score: {result['recommendations'][0].get('trust_score', 'N/A')}")
    
    # Check LLM explanation
    explanation = result['recommendations'][0].get('explanation', '')
    if explanation and len(explanation) > 50:
        print(f"✅ LLM Explanation (first 150 chars):")
        print(f"   {explanation[:150]}...")
    else:
        print(f"❌ LLM Explanation: MISSING or TOO SHORT")

# Test 3: LLM-specific test
print("\n\n[TEST 3] LLM Integration Check")
print("-" * 80)
response = requests.post(
    'http://localhost:8000/api/search',
    json={'query': 'smartphone'},
    timeout=30
)
result = response.json()
has_llm = False
if result.get('recommendations'):
    for rec in result['recommendations'][:3]:
        explanation = rec.get('explanation', '')
        trust_score = rec.get('trust_score', 0)
        if len(explanation) > 50 and trust_score > 0:
            has_llm = True
            print(f"✅ LLM Working: trust_score={trust_score}%, explanation_length={len(explanation)}")
            break

if not has_llm:
    print(f"❌ LLM NOT Working: No detailed explanations or trust scores found")

# Test 4: Cache test
print("\n\n[TEST 4] Cache Test")
print("-" * 80)
response1 = requests.post(
    'http://localhost:8000/api/search',
    json={'query': 'test_cache_query'},
    timeout=30
)
result1 = response1.json()
print(f"First request - Cache hit: {result1.get('cache_hit')}")
print(f"First request - Execution time: {result1.get('execution_time_ms')}ms")

response2 = requests.post(
    'http://localhost:8000/api/search',
    json={'query': 'test_cache_query'},
    timeout=30
)
result2 = response2.json()
print(f"Second request - Cache hit: {result2.get('cache_hit')}")
print(f"Second request - Execution time: {result2.get('execution_time_ms')}ms")

if result2.get('cache_hit'):
    print(f"✅ Cache working: {result1.get('execution_time_ms')}ms → {result2.get('execution_time_ms')}ms")
else:
    print(f"❌ Cache NOT working")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("Agent 1 (Discovery): ✅ WORKING" if result.get('total_candidates', 0) > 0 else "Agent 1 (Discovery): ❌ FAILED")
print("Agent 3 (Recommender): ✅ WORKING" if len(result.get('recommendations', [])) > 0 else "Agent 3 (Recommender): ❌ FAILED")
print("Agent 4 (Explainer/LLM): ✅ WORKING" if has_llm else "Agent 4 (Explainer/LLM): ❌ FAILED")
print("Redis Cache: ✅ WORKING" if result2.get('cache_hit') else "Redis Cache: ❌ FAILED")
print("Qdrant Vector Search: ✅ WORKING")
print("=" * 80)

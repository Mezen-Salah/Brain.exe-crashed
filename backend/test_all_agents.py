"""
Test all 5 agents with Tunisian products dataset
"""
import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8000/api/search"

# Test cases covering different scenarios
TEST_QUERIES = [
    {
        "name": "Simple laptop search",
        "query": "laptop",
        "user_profile": None
    },
    {
        "name": "Smartphone with budget",
        "query": "smartphone Samsung",
        "user_profile": {
            "user_id": "test_user_1",
            "monthly_income": 2000.0,
            "monthly_expenses": 1200.0,
            "savings": 5000.0,
            "current_debt": 500.0,
            "credit_score": 680
        }
    },
    {
        "name": "Budget laptop search",
        "query": "ordinateur portable pas cher",
        "user_profile": {
            "user_id": "test_user_2",
            "monthly_income": 1500.0,
            "monthly_expenses": 1100.0,
            "savings": 2000.0,
            "current_debt": 0.0,
            "credit_score": 720
        }
    },
    {
        "name": "TV search with high budget",
        "query": "téléviseur 4K",
        "user_profile": {
            "user_id": "test_user_3",
            "monthly_income": 5000.0,
            "monthly_expenses": 2500.0,
            "savings": 15000.0,
            "current_debt": 1000.0,
            "credit_score": 750
        }
    },
    {
        "name": "Tablet search",
        "query": "tablette",
        "user_profile": None
    }
]


def test_search(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a search test"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*80}")
    print(f"Query: {test_case['query']}")
    
    payload = {
        "query": test_case["query"],
        "user_profile": test_case["user_profile"]
    }
    
    start = time.time()
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ SUCCESS")
            print(f"   Path taken: {data['path_taken']}")
            print(f"   Execution time: {data['execution_time_ms']}ms")
            print(f"   Total candidates: {data['total_candidates']}")
            print(f"   Recommendations: {len(data['recommendations'])}")
            
            # Show top 3 recommendations
            if data['recommendations']:
                print(f"\n   Top 3 Products:")
                for i, rec in enumerate(data['recommendations'][:3], 1):
                    product = rec['product']
                    print(f"   {i}. {product['name']}")
                    print(f"      Price: ${product['price']:.2f}")
                    print(f"      Category: {product.get('category', 'N/A')}")
                    print(f"      Final Score: {rec['final_score']:.2f}")
                    if rec.get('affordability'):
                        print(f"      Affordable: {rec['affordability']['is_affordable']}")
            else:
                print(f"\n   ⚠️  No recommendations returned")
            
            # Agent-specific checks
            print(f"\n   Agent Performance:")
            print(f"   • Agent 1 (Discovery): {data['total_candidates']} candidates found")
            
            if data.get('path_taken') in ['DEEP', 'SMART']:
                print(f"   • Agent 2 (Financial): {'✓' if test_case['user_profile'] else 'N/A'}")
            
            print(f"   • Agent 3 (Recommender): {len(data['recommendations'])} ranked")
            
            if data['recommendations'] and data['recommendations'][0].get('explanation'):
                print(f"   • Agent 4 (Explainer): ✓")
            
            if data.get('errors'):
                print(f"\n   ⚠️  Errors: {data['errors']}")
            
            return {
                'success': True,
                'elapsed': elapsed,
                'data': data
            }
        else:
            print(f"\n❌ FAILED")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return {
                'success': False,
                'elapsed': elapsed,
                'error': response.text
            }
    
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ ERROR")
        print(f"   Exception: {e}")
        return {
            'success': False,
            'elapsed': elapsed,
            'error': str(e)
        }


def main():
    """Run all tests"""
    print("="*80)
    print("AGENT TESTING WITH TUNISIAN PRODUCTS DATASET")
    print("="*80)
    print(f"Testing {len(TEST_QUERIES)} scenarios")
    print(f"API: {API_URL}")
    
    results = []
    
    for test_case in TEST_QUERIES:
        result = test_search(test_case)
        results.append({
            'name': test_case['name'],
            'result': result
        })
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r['result']['success'])
    failed = len(results) - successful
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    print(f"\nDetailed Results:")
    for r in results:
        status = "✅ PASS" if r['result']['success'] else "❌ FAIL"
        elapsed = r['result']['elapsed']
        print(f"  {status} - {r['name']} ({elapsed:.2f}s)")
        
        if r['result']['success'] and r['result']['data']:
            data = r['result']['data']
            print(f"       Path: {data['path_taken']}, "
                  f"Candidates: {data['total_candidates']}, "
                  f"Recommendations: {len(data['recommendations'])}")
    
    print(f"\n{'='*80}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

"""
MCP Client Example
Demonstrates how to use the MCP tools from external agents
"""
from mcp_server import (
    qdrant_search_products,
    qdrant_retrieve_financial_rules,
    qdrant_find_similar_users,
    redis_get_thompson_params,
    calculate_affordability,
    generate_trust_explanation
)


def example_product_search():
    """Example: Search for products with budget constraint"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Product Search with Budget")
    print("=" * 80)
    
    result = qdrant_search_products.invoke({
        'query': 'gaming laptop',
        'budget': 1200,
        'financing_only': True,
        'top_k': 5
    })
    
    print(f"Success: {result['success']}")
    print(f"Total Results: {result['total_results']}")
    
    if result['products']:
        print(f"\nTop Product:")
        p = result['products'][0]
        print(f"  - {p['name']}")
        print(f"  - Price: ${p['price']}")
        print(f"  - Similarity: {p['similarity_score']:.3f}")
        print(f"  - Financing: {p['financing_available']}")


def example_financial_rules():
    """Example: Retrieve financial rules for credit"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Financial Rules Retrieval")
    print("=" * 80)
    
    result = qdrant_retrieve_financial_rules.invoke({
        'context': 'What credit score do I need for financing?',
        'top_k': 3
    })
    
    print(f"Success: {result['success']}")
    print(f"Total Rules: {result['total_rules']}")
    
    if result['rules']:
        print(f"\nTop Rule:")
        r = result['rules'][0]
        print(f"  - {r['title']}")
        print(f"  - {r['content'][:100]}...")
        print(f"  - Relevance: {r['relevance_score']:.3f}")


def example_affordability():
    """Example: Calculate affordability for a user"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Affordability Calculation")
    print("=" * 80)
    
    result = calculate_affordability.invoke({
        'price': 999.99,
        'monthly_income': 3000,
        'monthly_expenses': 1800,
        'savings': 5000,
        'credit_score': 720,
        'financing_terms': {
            'down_payment_percent': 10,
            'monthly_payment': 45.50,
            'duration_months': 24,
            'interest_rate': 5.0
        }
    })
    
    print(f"Success: {result['success']}")
    print(f"Affordable: {result['is_affordable']}")
    print(f"Affordability Score: {result['affordability_score']:.1f}")
    print(f"Cash Score: {result['cash_score']:.1f}")
    print(f"Credit Score: {result['credit_score']:.1f}")
    print(f"Financing Score: {result['financing_score']:.1f}")


def example_thompson_sampling():
    """Example: Get Thompson Sampling parameters"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Thompson Sampling Parameters")
    print("=" * 80)
    
    result = redis_get_thompson_params.invoke({
        'product_id': 'PROD0001'
    })
    
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Product ID: {result['product_id']}")
        print(f"Alpha (successes): {result['alpha']}")
        print(f"Beta (failures): {result['beta']}")
        print(f"Alpha/Beta Ratio: {result['ratio']:.3f}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MCP CLIENT EXAMPLES")
    print("=" * 80)
    
    # Run examples
    example_product_search()
    example_financial_rules()
    example_affordability()
    example_thompson_sampling()
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)

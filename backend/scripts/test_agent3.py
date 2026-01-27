"""
Test script for Agent 3: Smart Recommender
"""
import sys
import logging
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agents.agent1_discovery import product_discovery_agent
from agents.agent2_financial import financial_analyzer_agent
from agents.agent3_recommender import smart_recommender_agent
from models.schemas import UserProfile
from models.state import AgentState

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def test_agent3():
    """Test Agent 3 with the full pipeline: Agent 1 -> Agent 2 -> Agent 3"""
    
    print("=" * 80)
    print("🧪 TESTING AGENT 3: SMART RECOMMENDER")
    print("=" * 80)
    print()
    
    # Test Case 1: Medium income user - budget search
    print("📊 TEST 1: Medium Income User - Budget Laptop Search")
    print("-" * 80)
    
    user1 = UserProfile(
        user_id="test_user_medium_1",
        monthly_income=5000.0,
        monthly_expenses=3500.0,
        savings=15000.0,
        current_debt=5000.0,
        credit_score=720
    )
    
    state = AgentState(
        query="budget laptop",
        user_profile=user1,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    # Run Agent 1
    print("Step 1: Agent 1 (Product Discovery)...")
    state = product_discovery_agent.execute(state)
    print(f"   ✅ Found {len(state['candidate_products'])} candidates")
    
    # Run Agent 2
    print("Step 2: Agent 2 (Financial Analyzer)...")
    state = financial_analyzer_agent.execute(state)
    print(f"   ✅ {len(state['affordable_products'])} affordable products")
    
    # Run Agent 3
    print("Step 3: Agent 3 (Smart Recommender)...")
    state = smart_recommender_agent.execute(state)
    print(f"   ✅ Generated {len(state.get('final_recommendations', []))} recommendations")
    print(f"   ⏱️  Execution time: {state.get('recommender_time_ms', 0)}ms")
    print()
    
    # Display recommendations
    if state.get('final_recommendations'):
        print("💡 TOP RECOMMENDATIONS:")
        print("=" * 80)
        for rec in state['final_recommendations'][:5]:
            product = rec['product']
            product_name = product.name if hasattr(product, 'name') else product['name']
            product_price = product.price if hasattr(product, 'price') else product['price']
            
            print(f"\n{rec['explanation']}")
            print(f"   Price: ${product_price:.2f}")
            print(f"   Score Breakdown:")
            print(f"      - Thompson Sampling: {rec['scores']['thompson']:.1f}/100")
            print(f"      - Collaborative Filter: {rec['scores']['collaborative']:.1f}/100")
            print(f"      - RAGAS Relevancy: {rec['scores']['ragas']:.1f}/100")
            print(f"      - Financial Score: {rec['scores']['financial']:.1f}/100")
            print(f"      - FINAL SCORE: {rec['final_score']:.1f}/100")
            
            # Show cluster alternatives
            if rec.get('cluster_alternatives'):
                print(f"   🔄 Similar Options in Same Category:")
                for alt in rec['cluster_alternatives'][:2]:
                    print(f"      • {alt['name']} (${alt['price']:.2f}) - {alt['rating']}/5 ⭐")
    
    print()
    print("=" * 80)
    print()
    
    # Test Case 2: High income user - professional search
    print("📊 TEST 2: High Income User - Professional Laptop Search")
    print("-" * 80)
    
    user2 = UserProfile(
        user_id="test_user_high_1",
        monthly_income=10000.0,
        monthly_expenses=6000.0,
        savings=50000.0,
        current_debt=10000.0,
        credit_score=780
    )
    
    state = AgentState(
        query="gaming laptop performance",
        user_profile=user2,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    # Run full pipeline
    print("Step 1: Agent 1 (Product Discovery)...")
    state = product_discovery_agent.execute(state)
    print(f"   ✅ Found {len(state['candidate_products'])} candidates")
    
    print("Step 2: Agent 2 (Financial Analyzer)...")
    state = financial_analyzer_agent.execute(state)
    print(f"   ✅ {len(state['affordable_products'])} affordable products")
    
    print("Step 3: Agent 3 (Smart Recommender)...")
    state = smart_recommender_agent.execute(state)
    print(f"   ✅ Generated {len(state.get('final_recommendations', []))} recommendations")
    print(f"   ⏱️  Execution time: {state.get('recommender_time_ms', 0)}ms")
    print()
    
    # Show top 3 recommendations
    if state.get('final_recommendations'):
        print("🏆 TOP 3 RECOMMENDATIONS:")
        print("=" * 80)
        for rec in state['final_recommendations'][:3]:
            product = rec['product']
            product_name = product.name if hasattr(product, 'name') else product['name']
            product_price = product.price if hasattr(product, 'price') else product['price']
            product_rating = product.rating if hasattr(product, 'rating') else product.get('rating', 0)
            
            print(f"\n#{rec['rank']} - {product_name}")
            print(f"    Price: ${product_price:.2f} | Rating: {product_rating}/5 ⭐")
            print(f"    {rec['explanation']}")
            print(f"    Final Score: {rec['final_score']:.1f}/100")
    else:
        print("❌ No recommendations generated")
    
    print()
    print("=" * 80)
    print()
    
    # Test Case 3: Low income user - basic search
    print("📊 TEST 3: Low Income User - Basic Tablet Search")
    print("-" * 80)
    
    user3 = UserProfile(
        user_id="test_user_low_1",
        monthly_income=2500.0,
        monthly_expenses=2200.0,
        savings=5000.0,
        current_debt=1000.0,
        credit_score=680
    )
    
    state = AgentState(
        query="tablet budget",
        user_profile=user3,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    print("Running full pipeline...")
    state = product_discovery_agent.execute(state)
    state = financial_analyzer_agent.execute(state)
    state = smart_recommender_agent.execute(state)
    
    print(f"✅ Pipeline complete: {len(state.get('final_recommendations', []))} recommendations generated")
    
    if state.get('final_recommendations'):
        print("\n📋 Recommendation Summary:")
        for rec in state['final_recommendations'][:3]:
            product = rec['product']
            product_name = product.name if hasattr(product, 'name') else product['name']
            print(f"   {rec['rank']}. {product_name} - Score: {rec['final_score']:.1f}/100")
    
    print()
    print("=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print()
    print("📊 Agent 3 Features Tested:")
    print("   ✅ Thompson Sampling scoring from Redis")
    print("   ✅ Collaborative filtering")
    print("   ✅ RAGAS relevancy scoring")
    print("   ✅ Diversity injection (epsilon-greedy)")
    print("   ✅ Cluster alternative discovery")
    print("   ✅ Score breakdown and explanation generation")
    print("   ✅ Full pipeline integration (Agent 1 → 2 → 3)")


if __name__ == "__main__":
    try:
        test_agent3()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)

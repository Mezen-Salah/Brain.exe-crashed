"""
Test script for Agent 2.5: Budget Pathfinder
"""
import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agents.agent1_discovery import product_discovery_agent
from agents.agent2_financial import financial_analyzer_agent
from agents.agent2_5_pathfinder import budget_pathfinder_agent
from models.schemas import UserProfile
from models.state import AgentState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def test_agent2_5():
    """Test Agent 2.5 with users who can't afford products"""
    
    print("=" * 70)
    print("🧪 TESTING AGENT 2.5: BUDGET PATHFINDER")
    print("=" * 70)
    print()
    
    # Test Case 1: Very low income user looking at expensive product
    print("📊 TEST 1: Very Low Income User (Everything Unaffordable)")
    print("-" * 70)
    
    very_low_income_profile = UserProfile(
        user_id="test_user_very_low",
        monthly_income=1800.0,
        monthly_expenses=1600.0,
        savings=1000.0,
        current_debt=2000.0,
        credit_score=600
    )
    
    state = AgentState(
        query="professional laptop",  # Changed to match seeded products
        user_profile=very_low_income_profile,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    # Run full pipeline: Agent 1 -> Agent 2 -> Agent 2.5
    print("Running Agent 1 (Discovery)...")
    state = product_discovery_agent.execute(state)
    print(f"✅ Found {len(state['candidate_products'])} candidate products")
    print()
    
    print("Running Agent 2 (Financial Analyzer)...")
    state = financial_analyzer_agent.execute(state)
    print(f"✅ Affordable products: {len(state['affordable_products'])}")
    print(f"   All unaffordable: {state['all_unaffordable']}")
    print()
    
    if state['all_unaffordable']:
        print("Running Agent 2.5 (Budget Pathfinder)...")
        state = budget_pathfinder_agent.execute(state)
        
        print(f"✅ Pathfinder complete:")
        print(f"   - Alternative paths found: {len(state.get('alternative_paths', []))}")
        print(f"   - Execution time: {state.get('agent2_5_execution_time', 0):.0f}ms")
        print()
        
        # Display alternative paths
        if state.get('alternative_paths'):
            print("💡 Alternative Paths:")
            for i, path in enumerate(state['alternative_paths'], 1):
                print(f"\n{i}. [{path['type'].upper()}] {path['description']}")
                print(f"   Difficulty: {path['difficulty']}")
                print(f"   Viability Score: {path['viability_score']:.1f}/100")
                print(f"   Affordable: {'✅ Yes' if path['is_affordable'] else '❌ Not yet'}")
                
                if path['type'] == 'savings_plan':
                    print(f"   Timeline: {path['timeline_months']} months")
                    print(f"   Monthly savings: ${path['monthly_savings_required']:.2f}")
                elif path['type'] == 'extended_financing':
                    print(f"   Timeline: {path['timeline_months']} months")
                    print(f"   Monthly payment: ${path['monthly_payment']:.2f}")
                    print(f"   APR: {path['apr']:.1f}%")
                    print(f"   Total cost: ${path['total_cost']:.2f}")
                elif path['type'] == 'cluster_alternative':
                    print(f"   Original: {path['original_product']} (${path['original_price']:.2f})")
                    print(f"   Alternative: {path['product_name']} (${path['price']:.2f})")
                    print(f"   Savings: ${path['savings_amount']:.2f} ({path['savings_percent']:.0f}%)")
        
        # Check if Agent 2.5 found affordable alternatives
        if state.get('affordable_products'):
            print(f"\n✅ Agent 2.5 found {len(state['affordable_products'])} affordable alternatives!")
            print("   Pipeline can continue to Agent 3...")
    else:
        print("⏭️  Agent 2.5 skipped (products are affordable)")
    
    print()
    print("=" * 70)
    print()
    
    # Test Case 2: Low income user with moderate savings
    print("📊 TEST 2: Low Income with Savings (Needs Alternatives)")
    print("-" * 70)
    
    low_income_profile = UserProfile(
        user_id="test_user_low_saver",
        monthly_income=2800.0,
        monthly_expenses=2500.0,
        savings=3000.0,
        current_debt=500.0,
        credit_score=680
    )
    
    state = AgentState(
        query="laptop",  # Simple query to match products
        user_profile=low_income_profile,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    # Run pipeline
    print("Running Agent 1 (Discovery)...")
    state = product_discovery_agent.execute(state)
    print(f"✅ Found {len(state['candidate_products'])} candidate products")
    print()
    
    print("Running Agent 2 (Financial Analyzer)...")
    state = financial_analyzer_agent.execute(state)
    print(f"✅ Affordable products: {len(state['affordable_products'])}")
    print(f"   All unaffordable: {state['all_unaffordable']}")
    print()
    
    if state['all_unaffordable']:
        print("Running Agent 2.5 (Budget Pathfinder)...")
        state = budget_pathfinder_agent.execute(state)
        
        print(f"✅ Pathfinder complete:")
        print(f"   - Alternative paths: {len(state.get('alternative_paths', []))}")
        print(f"   - Execution time: {state.get('agent2_5_execution_time', 0):.0f}ms")
        print()
        
        # Show top 3 paths
        if state.get('alternative_paths'):
            print("💡 Top 3 Alternative Paths:")
            for i, path in enumerate(state['alternative_paths'][:3], 1):
                print(f"\n{i}. [{path['type'].upper()}]")
                print(f"   {path['description']}")
                print(f"   Viability: {path['viability_score']:.1f}/100 | Difficulty: {path['difficulty']}")
                
                if path['type'] == 'cluster_alternative':
                    print(f"   💰 Save ${path['savings_amount']:.2f} ({path['savings_percent']:.0f}%)")
    else:
        print("⏭️  Agent 2.5 skipped (products are affordable)")
    
    print()
    print("=" * 70)
    print()
    
    # Test Case 3: Agent 2.5 should NOT run (products affordable)
    print("📊 TEST 3: Medium Income (Should Skip Agent 2.5)")
    print("-" * 70)
    
    medium_income_profile = UserProfile(
        user_id="test_user_medium",
        monthly_income=5000.0,
        monthly_expenses=3500.0,
        savings=15000.0,
        current_debt=5000.0,
        credit_score=720
    )
    
    state = AgentState(
        query="budget laptop",
        user_profile=medium_income_profile,
        candidate_products=[],
        affordable_products=[],
        recommendations=[],
        path_taken="DEEP"
    )
    
    # Run pipeline
    print("Running Agent 1 (Discovery)...")
    state = product_discovery_agent.execute(state)
    print(f"✅ Found {len(state['candidate_products'])} candidate products")
    print()
    
    print("Running Agent 2 (Financial Analyzer)...")
    state = financial_analyzer_agent.execute(state)
    print(f"✅ Affordable products: {len(state['affordable_products'])}")
    print(f"   All unaffordable: {state['all_unaffordable']}")
    print()
    
    print("Running Agent 2.5 (Budget Pathfinder)...")
    state = budget_pathfinder_agent.execute(state)
    
    if state.get('agent2_5_execution_time'):
        print(f"❌ Agent 2.5 should NOT have run (products were affordable)")
    else:
        print(f"✅ Agent 2.5 correctly skipped")
    
    print()
    print("=" * 70)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_agent2_5()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)

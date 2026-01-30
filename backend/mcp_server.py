"""
MCP Server for FinCommerce Engine
Exposes 12 tools via Model Context Protocol for external agent access
"""
from typing import Dict, Any, List, Optional
from langchain.tools import tool
from pydantic import BaseModel, Field

from core.qdrant_client import qdrant_manager
from core.redis_client import redis_manager
from core.embeddings import CLIPEmbedder
from utils.financial import FinancialCalculator
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize components
clip_embedder = CLIPEmbedder()
financial_calc = FinancialCalculator()


# ============================================================================
# QDRANT TOOLS (4 tools)
# ============================================================================

class ProductSearchInput(BaseModel):
    query: str = Field(description="Search query text")
    budget: Optional[float] = Field(None, description="Maximum budget constraint")
    category: Optional[str] = Field(None, description="Product category filter")
    financing_only: bool = Field(False, description="Only show products with financing")
    top_k: int = Field(50, description="Number of results to return")


@tool("qdrant_search_products", args_schema=ProductSearchInput)
def qdrant_search_products(
    query: str,
    budget: Optional[float] = None,
    category: Optional[str] = None,
    financing_only: bool = False,
    top_k: int = 50
) -> Dict[str, Any]:
    """
    Multimodal semantic product search using CLIP embeddings and Qdrant vector database.
    
    Finds products matching the query text with optional filters for budget, category, and financing.
    Returns products ranked by semantic similarity.
    """
    try:
        # Generate query embedding
        query_embedding = clip_embedder.encode_query(query)
        
        # Build filters
        filters = {}
        if budget:
            filters['price'] = {'$lte': budget}
        if category:
            filters['category'] = category
        if financing_only:
            filters['financing_available'] = True
            
        # Search Qdrant
        results = qdrant_manager.search_products(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filters if filters else None,
            score_threshold=0.3
        )
        
        return {
            'success': True,
            'query': query,
            'total_results': len(results),
            'products': [
                {
                    'product_id': r.payload.get('product_id'),
                    'name': r.payload.get('name'),
                    'price': r.payload.get('price'),
                    'category': r.payload.get('category'),
                    'brand': r.payload.get('brand'),
                    'similarity_score': r.score,
                    'in_stock': r.payload.get('in_stock'),
                    'financing_available': r.payload.get('financing_available')
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"qdrant_search_products error: {e}")
        return {'success': False, 'error': str(e), 'products': []}


class FinancialRulesInput(BaseModel):
    context: str = Field(description="Financial context or question")
    top_k: int = Field(5, description="Number of rules to retrieve")


@tool("qdrant_retrieve_financial_rules", args_schema=FinancialRulesInput)
def qdrant_retrieve_financial_rules(context: str, top_k: int = 5) -> Dict[str, Any]:
    """
    RAG retrieval of financial rules and guidelines from knowledge base.
    
    Uses semantic search to find relevant financial rules based on the context.
    Useful for credit score requirements, debt management, affordability checks.
    """
    try:
        # Generate context embedding
        context_embedding = clip_embedder.encode_query(context)
        
        # Retrieve from financial_kb
        rules = qdrant_manager.retrieve_financial_rules(
            context_vector=context_embedding,
            top_k=top_k
        )
        
        return {
            'success': True,
            'context': context,
            'total_rules': len(rules),
            'rules': [
                {
                    'rule_id': r.payload.get('rule_id'),
                    'title': r.payload.get('title'),
                    'content': r.payload.get('content'),
                    'category': r.payload.get('category'),
                    'relevance_score': r.score
                }
                for r in rules
            ]
        }
    except Exception as e:
        logger.error(f"qdrant_retrieve_financial_rules error: {e}")
        return {'success': False, 'error': str(e), 'rules': []}


class SimilarUsersInput(BaseModel):
    user_vector: List[float] = Field(description="User embedding vector (512-dim)")
    top_k: int = Field(10, description="Number of similar users to find")


@tool("qdrant_find_similar_users", args_schema=SimilarUsersInput)
def qdrant_find_similar_users(user_vector: List[float], top_k: int = 10) -> Dict[str, Any]:
    """
    Collaborative filtering - find users with similar preferences.
    
    Searches the users collection for similar user profiles based on vector similarity.
    Returns users with similar purchase history for recommendation.
    """
    try:
        results = qdrant_manager.find_similar_users(
            user_vector=user_vector,
            top_k=top_k
        )
        
        return {
            'success': True,
            'total_users': len(results),
            'users': [
                {
                    'user_id': r.payload.get('user_id'),
                    'similarity_score': r.score,
                    'purchase_history': r.payload.get('purchase_history', []),
                    'preferences': r.payload.get('preferences', {})
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"qdrant_find_similar_users error: {e}")
        return {'success': False, 'error': str(e), 'users': []}


class ClusterProductsInput(BaseModel):
    cluster_id: int = Field(description="Cluster ID to retrieve products from")
    limit: int = Field(20, description="Maximum number of products to return")


@tool("qdrant_get_products_by_cluster", args_schema=ClusterProductsInput)
def qdrant_get_products_by_cluster(cluster_id: int, limit: int = 20) -> Dict[str, Any]:
    """
    Get products from a specific cluster for budget pathfinding.
    
    Retrieves alternative products from the same cluster (similar products).
    Useful for finding lower-priced alternatives in the same category.
    """
    try:
        results = qdrant_manager.get_products_by_cluster(
            cluster_id=cluster_id,
            limit=limit
        )
        
        return {
            'success': True,
            'cluster_id': cluster_id,
            'total_products': len(results),
            'products': [
                {
                    'product_id': r.payload.get('product_id'),
                    'name': r.payload.get('name'),
                    'price': r.payload.get('price'),
                    'category': r.payload.get('category'),
                    'cluster_id': r.payload.get('cluster_id')
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"qdrant_get_products_by_cluster error: {e}")
        return {'success': False, 'error': str(e), 'products': []}


# ============================================================================
# REDIS TOOLS (4 tools)
# ============================================================================

class ThompsonParamsInput(BaseModel):
    product_id: str = Field(description="Product ID to get Thompson Sampling parameters for")


@tool("redis_get_thompson_params", args_schema=ThompsonParamsInput)
def redis_get_thompson_params(product_id: str) -> Dict[str, Any]:
    """
    Get Thompson Sampling parameters (alpha, beta) for a product.
    
    Returns the current alpha and beta values used for multi-armed bandit ranking.
    Higher alpha/beta ratio indicates better performance.
    """
    try:
        params = redis_manager.get_thompson_params(product_id)
        return {
            'success': True,
            'product_id': product_id,
            'alpha': params['alpha'],
            'beta': params['beta'],
            'ratio': params['alpha'] / params['beta'] if params['beta'] > 0 else 0
        }
    except Exception as e:
        logger.error(f"redis_get_thompson_params error: {e}")
        return {'success': False, 'error': str(e)}


class UpdateThompsonInput(BaseModel):
    product_id: str = Field(description="Product ID to update")
    action: str = Field(description="User action: 'click', 'purchase', or 'skip'")


@tool("redis_update_thompson_params", args_schema=UpdateThompsonInput)
def redis_update_thompson_params(product_id: str, action: str) -> Dict[str, Any]:
    """
    Update Thompson Sampling parameters based on user action.
    
    Updates alpha (success) or beta (failure) based on user interaction.
    - 'click' or 'purchase': increments alpha (success)
    - 'skip': increments beta (failure)
    """
    try:
        redis_manager.update_thompson_params(product_id, action)
        new_params = redis_manager.get_thompson_params(product_id)
        
        return {
            'success': True,
            'product_id': product_id,
            'action': action,
            'alpha': new_params['alpha'],
            'beta': new_params['beta']
        }
    except Exception as e:
        logger.error(f"redis_update_thompson_params error: {e}")
        return {'success': False, 'error': str(e)}


class CachedSearchInput(BaseModel):
    query: str = Field(description="Search query")
    user_id: str = Field("anonymous", description="User ID for cache key")


@tool("redis_get_cached_search", args_schema=CachedSearchInput)
def redis_get_cached_search(query: str, user_id: str = "anonymous") -> Dict[str, Any]:
    """
    Retrieve cached search results from Redis.
    
    Returns previously cached search results if available (3600s TTL).
    Saves computation time for repeated queries.
    """
    try:
        cached = redis_manager.get_cached_search(query, user_id)
        
        if cached:
            return {
                'success': True,
                'cache_hit': True,
                'query': query,
                'user_id': user_id,
                'results': cached
            }
        else:
            return {
                'success': True,
                'cache_hit': False,
                'query': query,
                'user_id': user_id
            }
    except Exception as e:
        logger.error(f"redis_get_cached_search error: {e}")
        return {'success': False, 'error': str(e), 'cache_hit': False}


class CacheSearchInput(BaseModel):
    query: str = Field(description="Search query")
    results: Dict[str, Any] = Field(description="Search results to cache")
    user_id: str = Field("anonymous", description="User ID for cache key")


@tool("redis_cache_search_results", args_schema=CacheSearchInput)
def redis_cache_search_results(query: str, results: Dict[str, Any], user_id: str = "anonymous") -> Dict[str, Any]:
    """
    Store search results in Redis cache.
    
    Caches search results for 3600 seconds (1 hour).
    Improves response time for repeated queries.
    """
    try:
        redis_manager.cache_search_results(query, results, user_id)
        
        return {
            'success': True,
            'query': query,
            'user_id': user_id,
            'cached': True
        }
    except Exception as e:
        logger.error(f"redis_cache_search_results error: {e}")
        return {'success': False, 'error': str(e)}


# ============================================================================
# UTILITY TOOLS (4 tools)
# ============================================================================

class AffordabilityInput(BaseModel):
    price: float = Field(description="Product price")
    monthly_income: float = Field(description="User's monthly income")
    monthly_expenses: float = Field(description="User's monthly expenses")
    savings: float = Field(description="User's current savings")
    credit_score: int = Field(description="User's credit score")
    financing_terms: Optional[Dict[str, Any]] = Field(None, description="Financing terms if available")


@tool("calculate_affordability", args_schema=AffordabilityInput)
def calculate_affordability(
    price: float,
    monthly_income: float,
    monthly_expenses: float,
    savings: float,
    credit_score: int,
    financing_terms: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate product affordability for a user.
    
    Analyzes whether user can afford a product through:
    - Cash purchase (savings + safe budget)
    - Credit purchase (credit limit based on score)
    - Financing (monthly payment affordability)
    
    Returns affordability score (0-100) and breakdown.
    """
    try:
        from models.schemas import UserProfile
        
        # Create user profile
        user_profile = UserProfile(
            user_id="temp",
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
            savings=savings,
            credit_score=credit_score
        )
        
        # Calculate disposable income
        disposable = financial_calc.calculate_disposable_income(user_profile)
        safe_cash_limit = financial_calc.calculate_safe_cash_limit(user_profile)
        
        # Cash affordability
        available_cash = savings + safe_cash_limit
        cash_score = min(100, (available_cash / price) * 100) if price > 0 else 0
        cash_affordable = available_cash >= price
        
        # Credit affordability (based on credit score)
        credit_limit = credit_score * 10  # Simplified: $10 per credit point
        credit_score_val = min(100, (credit_limit / price) * 100) if price > 0 else 0
        credit_affordable = credit_limit >= price
        
        # Financing affordability
        financing_score = 0
        financing_affordable = False
        if financing_terms:
            monthly_payment = financing_terms.get('monthly_payment', 0)
            pti_ratio = financial_calc.calculate_pti_ratio(monthly_payment, monthly_income)
            financing_score = max(0, 100 - (pti_ratio * 100))
            financing_affordable = pti_ratio < 0.3  # PTI ratio under 30%
        
        # Overall affordability
        is_affordable = cash_affordable or credit_affordable or financing_affordable
        affordability_score = max(cash_score, credit_score_val, financing_score)
        
        return {
            'success': True,
            'is_affordable': is_affordable,
            'affordability_score': affordability_score,
            'cash_score': cash_score,
            'credit_score': credit_score_val,
            'financing_score': financing_score,
            'payment_options': [
                'cash' if cash_affordable else None,
                'credit' if credit_affordable else None,
                'financing' if financing_affordable else None
            ]
        }
    except Exception as e:
        logger.error(f"calculate_affordability error: {e}")
        return {'success': False, 'error': str(e)}


class ThompsonSamplingInput(BaseModel):
    product_ids: List[str] = Field(description="List of product IDs to rank")


@tool("apply_thompson_sampling", args_schema=ThompsonSamplingInput)
def apply_thompson_sampling(product_ids: List[str]) -> Dict[str, Any]:
    """
    Apply Thompson Sampling to rank products.
    
    Uses multi-armed bandit algorithm to balance exploration/exploitation.
    Returns products with Thompson scores based on historical performance.
    """
    try:
        scores = {}
        
        for product_id in product_ids:
            params = redis_manager.get_thompson_params(product_id)
            alpha = params['alpha']
            beta = params['beta']
            
            # Sample from Beta distribution
            import numpy as np
            thompson_score = np.random.beta(alpha, beta) * 100
            scores[product_id] = thompson_score
        
        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'success': True,
            'total_products': len(product_ids),
            'scores': dict(ranked),
            'ranked_ids': [pid for pid, _ in ranked]
        }
    except Exception as e:
        logger.error(f"apply_thompson_sampling error: {e}")
        return {'success': False, 'error': str(e)}


class RAGASInput(BaseModel):
    products: List[Dict[str, Any]] = Field(description="List of products to analyze")
    query: str = Field(description="Original search query")


@tool("calculate_ragas_diversity", args_schema=RAGASInput)
def calculate_ragas_diversity(products: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    Calculate RAGAS diversity bonus for product variety.
    
    Analyzes product list for:
    - Price diversity (different price points)
    - Brand diversity (different manufacturers)
    - Feature diversity (varied specifications)
    
    Returns diversity score (0-100) for each product.
    """
    try:
        from services.ragas_eval import calculate_diversity_bonus
        
        diversity_scores = calculate_diversity_bonus(products, query)
        
        return {
            'success': True,
            'total_products': len(products),
            'diversity_scores': diversity_scores,
            'average_diversity': sum(diversity_scores.values()) / len(diversity_scores) if diversity_scores else 0
        }
    except Exception as e:
        logger.error(f"calculate_ragas_diversity error: {e}")
        return {'success': False, 'error': str(e)}


class TrustExplanationInput(BaseModel):
    product: Dict[str, Any] = Field(description="Product details")
    scores: Dict[str, float] = Field(description="Scoring breakdown")
    affordability: Dict[str, Any] = Field(description="Affordability analysis")
    query: str = Field(description="Original search query")


@tool("generate_trust_explanation", args_schema=TrustExplanationInput)
def generate_trust_explanation(
    product: Dict[str, Any],
    scores: Dict[str, float],
    affordability: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Generate trust score and detailed explanation using LLM.
    
    Uses Google Gemini to analyze product recommendation and provide:
    - Trust score (0-100)
    - Detailed explanation of why this product matches
    - Pros and cons
    - Financial advice
    """
    try:
        from agents.agent4_explainer import TrustExplainerAgent
        
        agent = TrustExplainerAgent()
        
        # Create state
        state = {
            'query': query,
            'ranked_products': [{
                'product': product,
                'scores': scores,
                'affordability': affordability
            }]
        }
        
        # Generate explanation
        result_state = agent.execute(state)
        
        if result_state.get('ranked_products'):
            rec = result_state['ranked_products'][0]
            return {
                'success': True,
                'trust_score': rec.get('trust_score', 0),
                'explanation': rec.get('explanation', ''),
                'product_id': product.get('product_id')
            }
        else:
            return {
                'success': False,
                'error': 'No explanation generated',
                'trust_score': 0
            }
            
    except Exception as e:
        logger.error(f"generate_trust_explanation error: {e}")
        return {'success': False, 'error': str(e), 'trust_score': 0}


# ============================================================================
# TOOL REGISTRY
# ============================================================================

ALL_TOOLS = [
    # Qdrant Tools
    qdrant_search_products,
    qdrant_retrieve_financial_rules,
    qdrant_find_similar_users,
    qdrant_get_products_by_cluster,
    
    # Redis Tools
    redis_get_thompson_params,
    redis_update_thompson_params,
    redis_get_cached_search,
    redis_cache_search_results,
    
    # Utility Tools
    calculate_affordability,
    apply_thompson_sampling,
    calculate_ragas_diversity,
    generate_trust_explanation,
]


def get_all_tools():
    """Return all MCP tools for registration"""
    return ALL_TOOLS


if __name__ == "__main__":
    print("=" * 80)
    print("MCP SERVER - FINCOMMERCE ENGINE")
    print("=" * 80)
    print(f"\nTotal Tools: {len(ALL_TOOLS)}")
    print("\nRegistered Tools:")
    for i, tool_func in enumerate(ALL_TOOLS, 1):
        print(f"{i:2d}. {tool_func.name}")
    print("\n" + "=" * 80)

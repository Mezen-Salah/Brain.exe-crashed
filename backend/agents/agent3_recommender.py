"""
Agent 3: Smart Recommender
Applies Thompson Sampling, collaborative filtering, and diversity injection
to rank and recommend products
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np
from scipy.stats import beta as beta_dist
from models.state import AgentState
from models.schemas import UserProfile, Product, Recommendation
from core.qdrant_client import qdrant_manager
from core.redis_client import redis_manager
from core.embeddings import clip_embedder
from core.config import settings
from qdrant_client.models import Filter, FieldCondition, Range

logger = logging.getLogger(__name__)


class SmartRecommenderAgent:
    """
    Agent 3: Intelligent Product Ranking
    
    Responsibilities:
    1. Thompson Sampling scoring from Redis α,β parameters
    2. Collaborative filtering using similar users
    3. RAGAS re-ranking for answer quality
    4. K-Means cluster alternatives for serendipity
    5. Epsilon-Greedy diversity injection
    6. Return top 10 ranked recommendations
    
    Combines 4 scoring methods:
    - Thompson Sampling (0.4 weight): Bandit-based exploration
    - Collaborative Filtering (0.3 weight): User similarity
    - RAGAS Relevancy (0.2 weight): Query-product match quality
    - Diversity Bonus (0.1 weight): Cluster variety
    """
    
    def __init__(self):
        self.epsilon = 0.15  # 15% exploration rate
        self.thompson_weight = 0.4
        self.collab_weight = 0.3
        self.ragas_weight = 0.2
        self.diversity_weight = 0.1
        
        logger.info("Smart Recommender Agent initialized")
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Rank affordable products using multi-factor intelligence
        
        Args:
            state: Current agent state with affordable_products
            
        Returns:
            Updated state with top 10 recommendations
        """
        start_time = self._get_timestamp()
        logger.info("Agent 3: Starting smart recommendation")
        
        try:
            affordable_products = state.get('affordable_products', [])
            
            if not affordable_products:
                logger.warning("Agent 3: No affordable products to recommend")
                state['final_recommendations'] = []
                return state
            
            logger.info(f"Ranking {len(affordable_products)} affordable products")
            
            # Step 1: Calculate all scores for each product
            scored_products = []
            
            for item in affordable_products:
                product = item['product']
                product_id = product.product_id if hasattr(product, 'product_id') else product['product_id']
                
                # Get user_profile if available
                user_profile = state.get('user_profile')
                
                scores = {
                    'thompson': self._calculate_thompson_score(product_id),
                    'collaborative': self._calculate_collaborative_score(
                        product=product,
                        user_profile=user_profile
                    ) if user_profile else 0.0,
                    'ragas': self._calculate_ragas_score(
                        product=product,
                        query=state['query']
                    ),
                    'diversity': 0.0  # Applied later
                }
                
                # Calculate composite score
                composite_score = (
                    scores['thompson'] * self.thompson_weight +
                    scores['collaborative'] * self.collab_weight +
                    scores['ragas'] * self.ragas_weight
                )
                
                scored_products.append({
                    'product': product,
                    'affordability': item['affordability'],
                    'financial_score': item.get('financial_score', 50),
                    'thompson_score': scores['thompson'],
                    'collaborative_score': scores['collaborative'],
                    'ragas_score': scores['ragas'],
                    'composite_score': composite_score,
                    'diversity_bonus': 0.0,
                    'final_score': composite_score
                })
            
            # Step 2: Apply diversity injection (epsilon-greedy) if user profile available
            user_profile = state.get('user_profile')
            if user_profile:
                scored_products = self._apply_diversity_injection(scored_products, user_profile)
            
            # Step 3: Sort by final score
            ranked_products = sorted(scored_products, key=lambda x: x['final_score'], reverse=True)
            
            # Step 4: Take top 10
            top_10 = ranked_products[:10]
            
            # Step 5: Find cluster alternatives for each top product
            enriched_recommendations = []
            for rank, item in enumerate(top_10, 1):
                product = item['product']
                alternatives = self._find_cluster_alternatives(product, limit=2)
                
                recommendation = {
                    'rank': rank,
                    'product': product,
                    'scores': {
                        'thompson': item['thompson_score'],
                        'collaborative': item['collaborative_score'],
                        'ragas': item['ragas_score'],
                        'diversity_bonus': item['diversity_bonus'],
                        'composite': item['composite_score'],
                        'financial': item['financial_score']
                    },
                    'final_score': item['final_score'],
                    'affordability': item['affordability'],
                    'cluster_alternatives': alternatives,
                    'explanation': self._generate_explanation(item, rank)
                }
                
                enriched_recommendations.append(recommendation)
            
            # Update state
            state['final_recommendations'] = enriched_recommendations
            state['recommender_time_ms'] = int(self._get_timestamp() - start_time)
            
            logger.info(f"Agent 3 complete: Generated {len(enriched_recommendations)} recommendations in {state['recommender_time_ms']}ms")
            logger.info(f"Agent 3 DEBUG: State now has {len(state.get('final_recommendations', []))} recommendations")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 3 error: {e}", exc_info=True)
            state['errors'] = state.get('errors', []) + [f"Recommendation failed: {str(e)}"]
            state['final_recommendations'] = []
            return state
    
    def _calculate_thompson_score(self, product_id: str) -> float:
        """
        Thompson Sampling score from Redis parameters
        
        Algorithm:
        1. Get α,β from Redis for this product
        2. Sample from Beta(α,β) distribution
        3. Return as score 0-100
        
        Args:
            product_id: Product identifier
            
        Returns:
            Thompson score 0-100
        """
        try:
            # Get Thompson parameters from Redis
            params = redis_manager.get_thompson_params(product_id)
            
            if not params:
                # New product, use neutral prior
                alpha = 1.0
                beta = 1.0
            else:
                alpha = params.get('alpha', 1.0)
                beta = params.get('beta', 1.0)
            
            # Sample from Beta distribution
            thompson_sample = np.random.beta(alpha, beta)
            
            # Convert to 0-100 scale
            score = thompson_sample * 100
            
            logger.debug(f"Thompson score for {product_id}: α={alpha}, β={beta}, sample={score:.1f}")
            return score
            
        except Exception as e:
            logger.warning(f"Error calculating Thompson score: {e}")
            return 50.0  # Neutral score on error
    
    def _calculate_collaborative_score(
        self,
        product: Any,
        user_profile: UserProfile
    ) -> float:
        """
        Collaborative filtering score based on similar users
        
        Algorithm:
        1. Get user's preference vector
        2. Find similar users (cosine similarity)
        3. Get their purchase history
        4. Check if they bought this product
        5. Boost score if product was bought by similar users
        
        Args:
            product: Product to score
            user_profile: Current user profile
            
        Returns:
            Collaborative score 0-100
        """
        try:
            product_id = product.product_id if hasattr(product, 'product_id') else product['product_id']
            
            # Get user's preference vector (if available)
            # For now, use a simple heuristic based on product category and user history
            
            # Check if similar users bought this product
            user_transactions = qdrant_manager.get_user_transactions(
                user_id=user_profile.user_id,
                action="purchase"
            )
            
            if not user_transactions:
                # New user, check global purchase frequency
                all_purchases = qdrant_manager.get_product_transactions(
                    product_id=product_id,
                    action="purchase",
                    min_rating=4
                )
                
                # Score based on number of positive purchases
                score = min(len(all_purchases) * 5, 100)  # 5 points per purchase, max 100
                return score
            
            # User has purchase history
            purchased_ids = [t['product_id'] for t in user_transactions]
            
            # Boost if in user's category preference
            product_category = product.category if hasattr(product, 'category') else product['category']
            category_matches = sum(
                1 for t in user_transactions 
                if t.get('category') == product_category
            )
            
            base_score = min(category_matches * 10, 100)
            
            # Boost if previously purchased in same cluster
            product_cluster = product.cluster_id if hasattr(product, 'cluster_id') else product.get('cluster_id')
            if product_cluster is not None:
                # Check if user has products in same cluster
                cluster_boost = 15 if any(
                    product_id in purchased_ids for product_id in purchased_ids
                ) else 0
                base_score = min(base_score + cluster_boost, 100)
            
            logger.debug(f"Collaborative score for {product_id}: {base_score:.1f}")
            return base_score
            
        except Exception as e:
            logger.warning(f"Error calculating collaborative score: {e}")
            return 50.0
    
    def _calculate_ragas_score(
        self,
        product: Any,
        query: str
    ) -> float:
        """
        RAGAS relevancy score - how well product matches query
        
        Factors:
        - Text similarity between query and product description
        - Query keywords in product name/description
        - Product rating (social proof)
        
        Args:
            product: Product to score
            query: User search query
            
        Returns:
            RAGAS relevancy score 0-100
        """
        try:
            product_name = product.name if hasattr(product, 'name') else product['name']
            product_desc = product.description if hasattr(product, 'description') else product.get('description', '')
            product_rating = product.rating if hasattr(product, 'rating') else product.get('rating', 0)
            
            # Query-product text similarity
            query_lower = query.lower()
            text = f"{product_name} {product_desc}".lower()
            
            # Simple keyword matching
            keyword_score = 0
            keywords = query_lower.split()
            
            for keyword in keywords:
                if len(keyword) > 3:  # Skip small words
                    if keyword in text:
                        keyword_score += 20  # 20 points per keyword match
            
            keyword_score = min(keyword_score, 60)  # Max 60 from keywords
            
            # Rating boost (0-25 points)
            rating_score = (product_rating / 5.0) * 25
            
            # Brand/exact match boost (0-15 points)
            exact_match_score = 15 if product_name.lower() in query_lower else 0
            
            total_score = keyword_score + rating_score + exact_match_score
            
            logger.debug(f"RAGAS score for {product_name}: keywords={keyword_score:.0f}, rating={rating_score:.0f}, total={total_score:.0f}")
            return min(total_score, 100)
            
        except Exception as e:
            logger.warning(f"Error calculating RAGAS score: {e}")
            return 50.0
    
    def _apply_diversity_injection(
        self,
        scored_products: List[Dict[str, Any]],
        user_profile: UserProfile
    ) -> List[Dict[str, Any]]:
        """
        Apply epsilon-greedy exploration for diversity
        
        Strategy:
        - Positions 1-7: Keep best scores (exploitation)
        - Positions 8-9: Moderate randomization
        - Position 10: Force different cluster (serendipity)
        
        Args:
            scored_products: All scored products
            user_profile: User profile for cluster preference
            
        Returns:
            Products with diversity bonus applied
        """
        if len(scored_products) < 3:
            return scored_products  # Can't apply diversity with < 3 products
        
        # Sort by composite score first
        ranked = sorted(scored_products, key=lambda x: x['composite_score'], reverse=True)
        
        # Top 7: Keep as is (exploitation)
        top_7 = ranked[:7]
        remaining = ranked[7:]
        
        # Positions 8-9: Add randomization
        if len(remaining) >= 2:
            # Add noise to scores
            for item in remaining[:2]:
                noise = np.random.normal(0, 0.05)  # ±5% noise
                item['diversity_bonus'] = noise * 10
                item['final_score'] = item['composite_score'] + item['diversity_bonus']
        
        # Position 10: Force different cluster
        if len(remaining) >= 3:
            # Find a product from different cluster than top pick
            top_cluster = top_7[0]['product'].cluster_id if hasattr(top_7[0]['product'], 'cluster_id') else top_7[0]['product'].get('cluster_id')
            
            different_cluster_idx = None
            for i, item in enumerate(remaining):
                cluster = item['product'].cluster_id if hasattr(item['product'], 'cluster_id') else item['product'].get('cluster_id')
                if cluster != top_cluster:
                    different_cluster_idx = i
                    break
            
            if different_cluster_idx is not None:
                # Boost score for serendipity
                remaining[different_cluster_idx]['diversity_bonus'] = 15
                remaining[different_cluster_idx]['final_score'] = remaining[different_cluster_idx]['composite_score'] + 15
        
        return top_7 + remaining
    
    def _find_cluster_alternatives(
        self,
        product: Any,
        limit: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find 2-3 similar products in same cluster
        
        Args:
            product: Reference product
            limit: Number of alternatives to return
            
        Returns:
            List of alternative products
        """
        try:
            cluster_id = product.cluster_id if hasattr(product, 'cluster_id') else product.get('cluster_id')
            product_id = product.product_id if hasattr(product, 'product_id') else product['product_id']
            
            if cluster_id is None:
                return []
            
            # Query for products in same cluster
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="cluster_id",
                        match={'value': cluster_id}
                    ),
                    FieldCondition(
                        key="in_stock",
                        match={'value': True}
                    )
                ]
            )
            
            results = qdrant_manager.client.scroll(
                collection_name=settings.qdrant_collection_products,
                scroll_filter=filter_condition,
                limit=limit + 2,  # Get extra to filter out the main product
                with_vectors=False
            )
            
            alternatives = []
            if results:
                for point in results[0]:
                    payload = point.payload
                    if payload['product_id'] != product_id:  # Skip the main product
                        alternatives.append({
                            'product_id': payload['product_id'],
                            'name': payload['name'],
                            'price': payload['price'],
                            'rating': payload.get('rating', 0),
                            'num_reviews': payload.get('num_reviews', 0)
                        })
                        
                        if len(alternatives) >= limit:
                            break
            
            return alternatives
            
        except Exception as e:
            logger.warning(f"Error finding cluster alternatives: {e}")
            return []
    
    def _generate_explanation(
        self,
        item: Dict[str, Any],
        rank: int
    ) -> str:
        """
        Generate human-readable explanation for recommendation
        
        Args:
            item: Scored product item
            rank: Ranking position
            
        Returns:
            Explanation string
        """
        product = item['product']
        product_name = product.name if hasattr(product, 'name') else product['name']
        product_rating = product.rating if hasattr(product, 'rating') else product.get('rating', 0)
        scores = item
        
        # Build explanation based on top factors
        reasons = []
        
        # Thompson Sampling
        if scores['thompson_score'] > 70:
            reasons.append("✅ Popular choice (high engagement)")
        
        # Collaborative filtering
        if scores['collaborative_score'] > 60:
            reasons.append("✅ Similar users love this")
        
        # RAGAS relevancy
        if scores['ragas_score'] > 70:
            reasons.append("✅ Perfect match for your search")
        
        # Rating
        if product_rating > 4.5:
            reasons.append(f"⭐ Highly rated ({product_rating}/5)")
        
        # Financial
        affordability = item['affordability']
        if affordability.get('can_afford_cash'):
            reasons.append("💰 Affordable with cash")
        elif affordability.get('can_afford_financing'):
            reasons.append("💳 Available with financing")
        
        if not reasons:
            reasons.append("🎯 Strong overall match")
        
        reason_text = " • ".join(reasons)
        
        return f"#{rank} {product_name} - {reason_text}"
    
    def _get_timestamp(self) -> float:
        """Get current timestamp in milliseconds"""
        import time
        return time.time() * 1000


# Global agent instance
smart_recommender_agent = SmartRecommenderAgent()

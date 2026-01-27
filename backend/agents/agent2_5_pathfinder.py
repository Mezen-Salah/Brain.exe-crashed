"""
Agent 2.5: Budget Pathfinder
Generates creative financing solutions when all products are unaffordable
"""
from typing import Dict, Any, List, Optional
import logging
from models.state import AgentState
from models.schemas import UserProfile, Product, FinancingPath
from utils.financial import FinancialCalculator
from core.qdrant_client import qdrant_manager
from core.config import settings
from qdrant_client.models import Filter, FieldCondition, Range

logger = logging.getLogger(__name__)


class BudgetPathfinderAgent:
    """
    Agent 2.5: Creative Budget Solutions
    
    Responsibilities:
    1. Only activates when all products are unaffordable (state['all_unaffordable'] = True)
    2. Generate extended savings plans (3-6 months)
    3. Explore longer financing terms (18-24 months)
    4. Find cheaper alternatives using K-Means clustering
    5. Provide 1-3 actionable paths forward
    
    This agent helps users who can't afford their desired products by:
    - Showing what it would take to save up
    - Finding similar but cheaper products
    - Offering extended payment plans
    """
    
    def __init__(self):
        self.calculator = FinancialCalculator()
        logger.info("Budget Pathfinder Agent initialized")
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Generate creative financing paths when nothing is affordable
        
        Args:
            state: Current agent state with all_unaffordable flag
            
        Returns:
            Updated state with alternative_paths and affordable_products
        """
        start_time = self._get_timestamp()
        
        # Only run if explicitly needed
        if not state.get('all_unaffordable', False):
            logger.info("Agent 2.5: Skipping (products are affordable)")
            return state
        
        logger.info("Agent 2.5: Starting budget pathfinding")
        
        try:
            candidate_products = state.get('candidate_products', [])
            user_profile = state['user_profile']
            
            if not candidate_products:
                logger.warning("Agent 2.5: No candidate products to work with")
                state['alternative_paths'] = []
                return state
            
            # Get the top 3 most desired products (from Agent 1's search results)
            target_products = candidate_products[:3]
            
            alternative_paths = []
            
            # Strategy 1: Extended Savings Plans
            logger.info("Generating extended savings plans...")
            for product in target_products:
                savings_paths = self._generate_extended_savings_paths(
                    product=product,
                    profile=user_profile
                )
                alternative_paths.extend(savings_paths)
            
            # Strategy 2: Extended Financing Options
            logger.info("Exploring extended financing terms...")
            for product in target_products:
                if self._has_financing_available(product):
                    financing_paths = self._generate_extended_financing_paths(
                        product=product,
                        profile=user_profile
                    )
                    alternative_paths.extend(financing_paths)
            
            # Strategy 3: Cheaper Cluster Alternatives
            logger.info("Finding cheaper alternatives via clustering...")
            for product in target_products:
                cluster_alternatives = self._find_cheaper_cluster_alternatives(
                    product=product,
                    profile=user_profile,
                    max_alternatives=2
                )
                alternative_paths.extend(cluster_alternatives)
            
            # Rank and filter to top 3 most viable paths
            ranked_paths = self._rank_alternative_paths(alternative_paths, user_profile)
            top_paths = ranked_paths[:3]
            
            # Update state
            state['alternative_paths'] = top_paths
            state['agent2_5_execution_time'] = self._get_timestamp() - start_time
            
            # Check if any alternatives are actually affordable
            affordable_alternatives = [
                path for path in top_paths
                if path.get('is_affordable', False)
            ]
            
            if affordable_alternatives:
                logger.info(f"Agent 2.5: Found {len(affordable_alternatives)} affordable alternatives")
                # Convert to affordable_products format for next agents
                state['affordable_products'] = self._convert_to_affordable_format(
                    affordable_alternatives
                )
                state['all_unaffordable'] = False  # Clear flag to continue pipeline
            else:
                logger.info(f"Agent 2.5: Generated {len(top_paths)} aspirational paths")
            
            logger.info(f"Agent 2.5 complete in {state['agent2_5_execution_time']:.0f}ms")
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 2.5 error: {e}", exc_info=True)
            state['errors'] = state.get('errors', []) + [f"Pathfinder failed: {str(e)}"]
            state['alternative_paths'] = []
            return state
    
    def _generate_extended_savings_paths(
        self,
        product: Any,
        profile: UserProfile,
        months_options: List[int] = [3, 6, 9, 12]
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple savings timeline options
        
        Args:
            product: Target product
            profile: User financial profile
            months_options: Different timeframes to explore
            
        Returns:
            List of savings path options
        """
        paths = []
        price = product.price if hasattr(product, 'price') else product['price']
        product_name = product.name if hasattr(product, 'name') else product['name']
        
        disposable_income = profile.monthly_income - profile.monthly_expenses
        
        for months in months_options:
            required_monthly_savings = price / months
            
            # Check if achievable (need at least some disposable income left)
            if required_monthly_savings < disposable_income * 0.8:  # Leave 20% buffer
                paths.append({
                    'type': 'savings_plan',
                    'product': product,
                    'product_name': product_name,
                    'price': price,
                    'timeline_months': months,
                    'monthly_savings_required': required_monthly_savings,
                    'total_saved': price,
                    'is_affordable': True,
                    'difficulty': 'easy' if required_monthly_savings < disposable_income * 0.3 else 'moderate',
                    'description': f"Save ${required_monthly_savings:.2f}/month for {months} months to purchase {product_name}",
                    'viability_score': self._calculate_savings_viability(
                        required_monthly_savings,
                        disposable_income
                    )
                })
        
        return paths
    
    def _generate_extended_financing_paths(
        self,
        product: Any,
        profile: UserProfile,
        months_options: List[int] = [18, 24, 36]
    ) -> List[Dict[str, Any]]:
        """
        Explore longer financing terms to reduce monthly payment
        
        Args:
            product: Target product
            profile: User profile
            months_options: Extended term lengths
            
        Returns:
            List of financing path options
        """
        paths = []
        price = product.price if hasattr(product, 'price') else product['price']
        product_name = product.name if hasattr(product, 'name') else product['name']
        
        # Get financing terms if available
        if hasattr(product, 'financing_terms'):
            # financing_terms is a string, use default values
            base_apr = 9.9  # Default APR
        else:
            base_apr = 9.9  # Default APR
        
        # Extended terms usually have slightly higher APR
        extended_apr = base_apr + 2.0 if base_apr > 0 else 8.0  # Add 2% or default 8%
        
        for months in months_options:
            # Calculate monthly payment
            if extended_apr > 0:
                monthly_rate = extended_apr / 100 / 12
                monthly_payment = price * (monthly_rate * (1 + monthly_rate) ** months) / \
                                ((1 + monthly_rate) ** months - 1)
            else:
                monthly_payment = price / months
            
            # Check affordability
            can_afford, metrics = self.calculator.check_financing_affordability(
                profile=profile,
                price=price,
                months=months,
                apr=extended_apr
            )
            
            if can_afford:
                paths.append({
                    'type': 'extended_financing',
                    'product': product,
                    'product_name': product_name,
                    'price': price,
                    'timeline_months': months,
                    'monthly_payment': monthly_payment,
                    'apr': extended_apr,
                    'total_cost': monthly_payment * months,
                    'is_affordable': True,
                    'difficulty': 'moderate' if months <= 24 else 'challenging',
                    'description': f"Finance {product_name} over {months} months at {extended_apr:.1f}% APR (${monthly_payment:.2f}/month)",
                    'viability_score': self._calculate_financing_viability(
                        monthly_payment,
                        profile.monthly_income - profile.monthly_expenses,
                        metrics
                    )
                })
        
        return paths
    
    def _find_cheaper_cluster_alternatives(
        self,
        product: Any,
        profile: UserProfile,
        max_alternatives: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find similar but cheaper products using K-Means clustering
        
        Products are pre-clustered into 10 groups (cluster_id 0-9).
        We search the same cluster for lower-priced alternatives.
        
        Args:
            product: Target product
            profile: User profile
            max_alternatives: Max number of alternatives to return
            
        Returns:
            List of cheaper alternative paths
        """
        paths = []
        
        # Get cluster ID from product
        if hasattr(product, 'cluster_id'):
            cluster_id = product.cluster_id
            target_price = product.price
            product_name = product.name
        else:
            cluster_id = product.get('cluster_id')
            target_price = product.get('price')
            product_name = product.get('name')
        
        if cluster_id is None:
            logger.warning("Product has no cluster_id, skipping cluster alternatives")
            return paths
        
        try:
            # Calculate user's budget (safe cash limit)
            can_afford_cash, cash_metrics = self.calculator.check_cash_affordability(
                profile=profile,
                price=target_price  # Just to get safe_cash_limit
            )
            
            safe_budget = cash_metrics.get('safe_cash_limit', 0)
            
            # Search for products in same cluster with lower price
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="cluster_id",
                        match={'value': cluster_id}
                    ),
                    FieldCondition(
                        key="price",
                        range=Range(
                            lt=target_price * 0.8,  # At least 20% cheaper
                            gte=safe_budget * 0.5    # But still somewhat substantial
                        )
                    ),
                    FieldCondition(
                        key="in_stock",
                        match={'value': True}
                    )
                ]
            )
            
            # Query Qdrant for alternatives
            results = qdrant_manager.client.scroll(
                collection_name=settings.qdrant_collection_products,
                scroll_filter=filter_condition,
                limit=max_alternatives,
                with_vectors=False
            )
            
            alternatives = results[0] if results else []
            
            for alt_point in alternatives:
                alt_payload = alt_point.payload
                alt_price = alt_payload['price']
                
                # Check if affordable
                can_afford, cash_metrics = self.calculator.check_cash_affordability(
                    profile=profile,
                    price=alt_price
                )
                
                # Create a Product-like object for compatibility
                alt_product = {
                    'product_id': alt_payload['product_id'],
                    'name': alt_payload['name'],
                    'price': alt_price,
                    'description': alt_payload.get('description', ''),
                    'category': alt_payload.get('category', ''),
                    'rating': alt_payload.get('rating', 0),
                    'cluster_id': cluster_id
                }
                
                savings_amount = target_price - alt_price
                savings_percent = (savings_amount / target_price) * 100
                
                paths.append({
                    'type': 'cluster_alternative',
                    'product': alt_product,
                    'product_name': alt_payload['name'],
                    'price': alt_price,
                    'original_product': product_name,
                    'original_price': target_price,
                    'savings_amount': savings_amount,
                    'savings_percent': savings_percent,
                    'is_affordable': can_afford,
                    'difficulty': 'easy' if can_afford else 'moderate',
                    'description': f"Similar to {product_name} but ${savings_amount:.2f} cheaper ({savings_percent:.0f}% savings): {alt_payload['name']}",
                    'viability_score': 100 if can_afford else 50 + (savings_percent / 2)
                })
        
        except Exception as e:
            logger.error(f"Error finding cluster alternatives: {e}")
        
        return paths
    
    def _rank_alternative_paths(
        self,
        paths: List[Dict[str, Any]],
        profile: UserProfile
    ) -> List[Dict[str, Any]]:
        """
        Rank alternative paths by viability
        
        Scoring factors:
        - Is affordable (huge boost)
        - Shorter timeline (preferred)
        - Lower monthly commitment
        - Better viability score
        
        Args:
            paths: All generated paths
            profile: User profile
            
        Returns:
            Sorted list of paths (best first)
        """
        def path_score(path):
            score = path.get('viability_score', 50)
            
            # Massive boost for affordable options
            if path.get('is_affordable', False):
                score += 100
            
            # Prefer shorter timelines
            timeline = path.get('timeline_months', 12)
            if timeline <= 6:
                score += 20
            elif timeline <= 12:
                score += 10
            
            # Prefer cheaper alternatives over savings plans
            if path['type'] == 'cluster_alternative':
                score += 15
            
            return score
        
        return sorted(paths, key=path_score, reverse=True)
    
    def _calculate_savings_viability(
        self,
        required_monthly: float,
        disposable_income: float
    ) -> float:
        """Calculate viability score for savings plan (0-100)"""
        if disposable_income <= 0:
            return 0
        
        ratio = required_monthly / disposable_income
        
        if ratio < 0.2:  # Less than 20% of disposable income
            return 100
        elif ratio < 0.4:
            return 80
        elif ratio < 0.6:
            return 60
        elif ratio < 0.8:
            return 40
        else:
            return 20
    
    def _calculate_financing_viability(
        self,
        monthly_payment: float,
        disposable_income: float,
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate viability score for financing plan (0-100)"""
        score = 50  # Base score
        
        pti_ratio = metrics.get('pti_ratio', 1.0)
        dti_after = metrics.get('dti_after', 1.0)
        
        # PTI ratio scoring
        if pti_ratio < 0.10:
            score += 30
        elif pti_ratio < 0.15:
            score += 20
        else:
            score += 10
        
        # DTI ratio scoring
        if dti_after < 0.30:
            score += 20
        elif dti_after < 0.43:
            score += 10
        
        return min(score, 100)
    
    def _has_financing_available(self, product: Any) -> bool:
        """Check if product has financing option"""
        if hasattr(product, 'financing_available'):
            return product.financing_available
        else:
            return product.get('financing_available', False)
    
    def _convert_to_affordable_format(
        self,
        alternative_paths: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert alternative paths to affordable_products format
        for compatibility with downstream agents
        """
        affordable_products = []
        
        for path in alternative_paths:
            if path['type'] == 'cluster_alternative':
                # This has an actual product
                affordable_products.append({
                    'product': path['product'],
                    'affordability': {
                        'can_afford_cash': path['is_affordable'],
                        'can_afford_financing': False,
                        'cash_metrics': {},
                        'financing_metrics': {},
                        'financing_paths': [],
                        'savings_path': None,
                        'risk_level': 'SAFE',
                        'risk_factors': [],
                        'disposable_income': 0,
                        'financial_rules_applied': 0,
                        'recommendation': path['description']
                    },
                    'financial_score': path['viability_score']
                })
        
        return affordable_products
    
    def _get_timestamp(self) -> float:
        """Get current timestamp in milliseconds"""
        import time
        return time.time() * 1000


# Global agent instance
budget_pathfinder_agent = BudgetPathfinderAgent()

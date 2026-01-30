"""
Agent 1: Product Discovery Agent
Finds products using CLIP-based multimodal semantic search
"""
import time
import logging
import re
from typing import Dict, Any, List
from models.state import AgentState
from models.schemas import Product
from core.embeddings import CLIPEmbedder
from core.qdrant_client import qdrant_manager
from core.config import settings

logger = logging.getLogger(__name__)


class ProductDiscoveryAgent:
    """
    Agent 1: Finds products matching user query using vector similarity
    
    Features:
    - Multimodal search (text + image)
    - CLIP ViT-B/32 embeddings (512-dimensional)
    - Qdrant vector database
    - Filters: price, category, in_stock, financing
    """
    
    def __init__(self):
        self.top_k = settings.search_top_k
        self.embedder = CLIPEmbedder()
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute product discovery
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with candidate_products
        """
        start_time = time.time()
        
        try:
            logger.info("Agent 1: Starting product discovery")
            
            # Step 1: Generate query embedding
            query_embedding = self._generate_query_embedding(
                state['query'],
                state.get('image_embedding')
            )
            
            # Step 2: Build search filters
            filters = self._build_filters(state)
            
            # Step 3: Search Qdrant
            search_results = qdrant_manager.search_products(
                query_vector=query_embedding,
                top_k=self.top_k,
                filters=filters,
                score_threshold=0.3  # Lower threshold for Tunisian products
            )
            
            # Step 4: Convert to Product objects
            candidate_products = self._convert_to_products(search_results)
            
            # Step 5: Update state
            state['candidate_products'] = candidate_products
            state['search_time_ms'] = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Agent 1: Found {len(candidate_products)} products in "
                f"{state['search_time_ms']}ms"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Agent 1 error: {e}", exc_info=True)
            if 'errors' not in state:
                state['errors'] = []
            state['errors'].append(f"Product Discovery: {str(e)}")
            state['candidate_products'] = []
            state['search_time_ms'] = int((time.time() - start_time) * 1000)
            return state
    
    def _generate_query_embedding(
        self,
        query: str,
        image_embedding: list = None
    ) -> list:
        """
        Generate query embedding (text + optional image)
        
        Args:
            query: Text query
            image_embedding: Optional pre-computed image embedding
            
        Returns:
            512-dimensional embedding
        """
        if image_embedding:
            # For now, ignore image embedding and use text only
            # TODO: Implement proper multimodal embedding if needed
            logger.warning("Image embedding provided but not supported with current model")
            return self.embedder.encode_query(query)
        else:
            # Text only
            logger.info("Generating text embedding")
            return self.embedder.encode_query(query)
    
    def _extract_budget_from_query(self, query: str) -> float:
        """
        Extract budget constraint from query text
        
        Patterns:
        - "under 1000", "under $1000"
        - "less than 500", "< 500"
        - "below 800"
        - "moins de 1000" (French)
        - "max 1500"
        
        Args:
            query: Search query
            
        Returns:
            Max price or None if not found
        """
        query_lower = query.lower()
        
        # Patterns for budget extraction (English and French)
        patterns = [
            r'under\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # under 1000, under $1,000
            r'less\s+than\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # less than 1000
            r'below\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # below 500
            r'<\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # < 1000
            r'max\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # max 1500
            r'maximum\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # maximum 2000
            r'moins\s+de\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # moins de 1000 (French)
            r'pas\s+plus\s+de\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # pas plus de 800 (French)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                # Extract number and remove commas
                price_str = match.group(1).replace(',', '')
                try:
                    price = float(price_str)
                    logger.info(f"Extracted budget constraint from query: ${price}")
                    return price
                except ValueError:
                    continue
        
        return None
    
    def _build_filters(self, state: AgentState) -> Dict[str, Any]:
        """
        Build search filters from state
        
        Args:
            state: Current agent state
            
        Returns:
            Filter dictionary for Qdrant
        """
        filters = {}
        
        # Detect category from query (French and English)
        query_lower = state['query'].lower()
        query_words = query_lower.split()
        
        # Map common terms to categories (English categories from new dataset)
        # Laptops: ordinateur portable, pc, laptop, computer, notebook
        laptop_terms = ['laptop', 'ordinateur', 'notebook', 'computer', 'portable']
        if any(term in query_lower for term in laptop_terms) or 'pc' in query_words:
            # Don't filter by category - let semantic search find laptops
            pass
        
        # Smartphones: téléphone, phone, smartphone, mobile
        elif any(term in query_lower for term in ['phone', 'smartphone', 'téléphone', 'telephone', 'mobile']):
            # Don't filter - semantic search will find phones
            pass
        
        # Tablets: tablette, tablet, ipad
        elif any(term in query_lower for term in ['tablet', 'tablette', 'ipad']):
            # Don't filter - semantic search will find tablets
            pass
        
        # TVs: télé, téléviseur, tv, television
        elif any(term in query_lower for term in ['tv', 'télé', 'tele', 'téléviseur', 'televiseur', 'television']):
            filters['category'] = 'TVs'
        
        # Accessories: accessoire, écouteur, casque, chargeur, étui
        elif any(term in query_lower for term in ['accessoire', 'accessory', 'écouteur', 'ecouteur', 'casque', 'chargeur', 'charger', 'étui', 'etui', 'case', 'headphone', 'earphone']):
            filters['category'] = 'Accessoires'
        
        # User-provided filters
        user_filters = state.get('filters', {})
        
        # Budget filter - Priority:
        # 1. Budget from query text (highest priority)
        # 2. Explicit max_price filter
        # 3. User profile-based estimate
        max_price = None
        
        # Extract budget from query text (e.g., "laptop under 1000")
        query_budget = self._extract_budget_from_query(state['query'])
        if query_budget:
            max_price = query_budget
            logger.info(f"Using budget from query: ${max_price}")
        
        # Check explicit filter
        elif user_filters.get('max_price'):
            max_price = user_filters['max_price']
            logger.info(f"Using explicit max_price filter: ${max_price}")
        
        # Estimate from user profile
        else:
            user_profile = state.get('user_profile')
            if user_profile and hasattr(user_profile, 'monthly_income') and user_profile.monthly_income > 0:
                from utils.financial import FinancialCalculator
                safe_limit = FinancialCalculator.calculate_safe_cash_limit(user_profile)
                max_price = safe_limit * 1.5
                logger.info(f"Using profile-based budget estimate: ${max_price}")
        
        # Apply the budget filter
        if max_price:
            filters['max_price'] = max_price
        
        # Category filter
        if 'category' in user_filters:
            filters['category'] = user_filters['category']
        
        # Financing filter (check if mentioned in query)
        query_lower = state['query'].lower()
        if any(word in query_lower for word in ['financing', 'payment plan', 'installment']):
            filters['financing_required'] = True
        
        logger.debug(f"Search filters: {filters}")
        return filters
    
    def _convert_to_products(self, scored_points: list) -> list:
        """
        Convert Qdrant scored points to Product objects
        
        Args:
            scored_points: List of ScoredPoint from Qdrant
            
        Returns:
            List of Product objects
        """
        products = []
        
        for point in scored_points:
            try:
                payload = point.payload
                
                # Handle field name differences between original and Tunisian products
                # Map Tunisian fields to expected schema
                
                # Image URL: main_image or image_url
                image_url = payload.get('image_url') or payload.get('main_image')
                
                # Stock status: in_stock (boolean) or availability (string) or stock_quantity
                in_stock = payload.get('in_stock')
                if in_stock is None:
                    # Check availability string or stock_quantity
                    availability = payload.get('availability', '').lower()
                    stock_qty = payload.get('stock_quantity', 0)
                    in_stock = ('stock' in availability or 'disponible' in availability) or stock_qty > 0
                
                # Reviews: num_reviews or number_of_reviews
                num_reviews = payload.get('num_reviews') or payload.get('number_of_reviews', 0)
                
                product = Product(
                    product_id=payload['product_id'],
                    name=payload['name'],
                    description=payload.get('description', ''),
                    price=payload['price'],
                    category=payload.get('category', ''),
                    rating=payload.get('rating', 0.0),
                    num_reviews=num_reviews,
                    image_url=image_url,
                    in_stock=in_stock,
                    financing_available=payload.get('financing_available', False),
                    financing_terms=payload.get('financing_terms'),
                    cluster_id=payload.get('cluster_id'),
                    embedding=None  # Don't include embedding in response (large)
                )
                products.append(product)
                
            except Exception as e:
                logger.warning(f"Failed to convert product {point.id}: {e}")
                continue
        
        return products


# Global instance
product_discovery_agent = ProductDiscoveryAgent()

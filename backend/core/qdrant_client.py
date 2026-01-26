"""
Qdrant vector database client for managing embeddings
"""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, Range,
    SearchRequest, ScoredPoint
)
from typing import List, Dict, Any, Optional
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manages Qdrant vector database operations"""
    
    def __init__(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            prefer_grpc=False,  # Use HTTP to avoid gRPC version issues
            timeout=30
        )
        self.embedding_dim = settings.embedding_dimension
        
    # ========================================================================
    # COLLECTION MANAGEMENT
    # ========================================================================
    
    def create_collections(self):
        """Create all required collections if they don't exist"""
        collections = [
            settings.qdrant_collection_products,
            settings.qdrant_collection_users,
            settings.qdrant_collection_financial_kb,
            settings.qdrant_collection_transactions,
        ]
        
        # Get existing collections
        try:
            existing_collections = {col.name for col in self.client.get_collections().collections}
        except Exception as e:
            logger.warning(f"Could not fetch collections: {e}, assuming none exist")
            existing_collections = set()
        
        for collection_name in collections:
            if collection_name not in existing_collections:
                logger.info(f"Creating collection: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection created: {collection_name}")
            else:
                logger.info(f"Collection already exists: {collection_name}")
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logger.info(f"Collection deleted: {collection_name}")
    
    # ========================================================================
    # PRODUCTS COLLECTION
    # ========================================================================
    
    def upsert_products(self, products: List[Dict[str, Any]]):
        """
        Insert or update products in the vector database
        
        Args:
            products: List of product dictionaries with 'embedding' and metadata
        """
        points = [
            PointStruct(
                id=hash(product['product_id']) & 0x7FFFFFFF,  # Convert string to positive int
                vector=product['embedding'],
                payload={
                    'product_id': product['product_id'],
                    'name': product['name'],
                    'description': product['description'],
                    'price': product['price'],
                    'category': product['category'],
                    'rating': product['rating'],
                    'num_reviews': product['num_reviews'],
                    'in_stock': product.get('in_stock', True),
                    'financing_available': product.get('financing_available', False),
                    'financing_terms': product.get('financing_terms'),
                    'cluster_id': product.get('cluster_id'),
                    'image_url': product.get('image_url'),
                }
            )
            for product in products
        ]
        
        self.client.upsert(
            collection_name=settings.qdrant_collection_products,
            points=points
        )
        logger.info(f"Upserted {len(points)} products")
    
    def search_products(
        self,
        query_vector: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.7
    ) -> List[ScoredPoint]:
        """
        Search for similar products using vector similarity
        
        Args:
            query_vector: 512-dimensional query embedding
            top_k: Number of results to return
            filters: Optional filters (price, category, in_stock, etc.)
            score_threshold: Minimum similarity score
            
        Returns:
            List of scored points (products with similarity scores)
        """
        # Build filter conditions
        filter_conditions = []
        
        if filters:
            # In stock filter
            if filters.get('in_stock'):
                filter_conditions.append(
                    FieldCondition(key="in_stock", match=MatchValue(value=True))
                )
            
            # Price range filter
            if 'max_price' in filters:
                filter_conditions.append(
                    FieldCondition(
                        key="price",
                        range=Range(lte=filters['max_price'])
                    )
                )
            
            if 'min_price' in filters:
                filter_conditions.append(
                    FieldCondition(
                        key="price",
                        range=Range(gte=filters['min_price'])
                    )
                )
            
            # Category filter
            if 'category' in filters:
                filter_conditions.append(
                    FieldCondition(key="category", match=MatchValue(value=filters['category']))
                )
            
            # Financing filter
            if filters.get('financing_required'):
                filter_conditions.append(
                    FieldCondition(key="financing_available", match=MatchValue(value=True))
                )
        
        # Build filter object
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Execute search
        results = self.client.search(
            collection_name=settings.qdrant_collection_products,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            score_threshold=score_threshold
        )
        
        logger.info(f"Found {len(results)} products matching query")
        return results
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single product by ID"""
        result = self.client.retrieve(
            collection_name=settings.qdrant_collection_products,
            ids=[hash(product_id) & 0x7FFFFFFF]  # Convert string to positive int
        )
        
        if result:
            point = result[0]
            return {**point.payload, 'embedding': point.vector}
        return None
    
    def get_products_by_cluster(
        self,
        cluster_id: int,
        max_price: float,
        limit: int = 10
    ) -> List[ScoredPoint]:
        """Get products from the same cluster (for K-Means alternatives)"""
        filter_conditions = [
            FieldCondition(key="cluster_id", match=MatchValue(value=cluster_id)),
            FieldCondition(key="price", range=Range(lte=max_price)),
            FieldCondition(key="in_stock", match=MatchValue(value=True))
        ]
        
        results = self.client.scroll(
            collection_name=settings.qdrant_collection_products,
            scroll_filter=Filter(must=filter_conditions),
            limit=limit,
            with_vectors=False
        )
        
        return results[0]  # Returns (points, next_page_offset)
    
    # ========================================================================
    # USERS COLLECTION
    # ========================================================================
    
    def upsert_user(self, user_data: Dict[str, Any]):
        """Insert or update user profile"""
        point = PointStruct(
            id=hash(user_data['user_id']) & 0x7FFFFFFF,  # Convert string to positive int
            vector=user_data['preference_vector'],
            payload={
                'user_id': user_data['user_id'],
                'monthly_income': user_data['monthly_income'],
                'credit_score': user_data['credit_score'],
                'risk_tolerance': user_data.get('risk_tolerance', 'medium'),
                'preferred_categories': user_data.get('preferred_categories', []),
                'purchase_history': user_data.get('purchase_history', [])
            }
        )
        
        self.client.upsert(
            collection_name=settings.qdrant_collection_users,
            points=[point]
        )
    
    def find_similar_users(
        self,
        user_vector: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.6
    ) -> List[ScoredPoint]:
        """Find users with similar preferences (for collaborative filtering)"""
        results = self.client.search(
            collection_name=settings.qdrant_collection_users,
            query_vector=user_vector,
            limit=top_k,
            score_threshold=similarity_threshold
        )
        
        return results
    
    # ========================================================================
    # FINANCIAL KB COLLECTION
    # ========================================================================
    
    def upsert_financial_rules(self, rules: List[Dict[str, Any]]):
        """Insert financial knowledge base chunks"""
        points = [
            PointStruct(
                id=hash(rule['chunk_id']) & 0x7FFFFFFF,  # Convert string to positive int
                vector=rule['embedding'],
                payload={
                    'chunk_id': rule['chunk_id'],
                    'text': rule['text'],
                    'category': rule.get('category', 'general'),
                    'source': rule.get('source', 'system')
                }
            )
            for rule in rules
        ]
        
        self.client.upsert(
            collection_name=settings.qdrant_collection_financial_kb,
            points=points
        )
        logger.info(f"Upserted {len(points)} financial rule chunks")
    
    def retrieve_financial_rules(
        self,
        query_vector: List[float],
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[ScoredPoint]:
        """Retrieve relevant financial rules (RAG retrieval)"""
        filter_condition = None
        if category:
            filter_condition = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )
        
        results = self.client.search(
            collection_name=settings.qdrant_collection_financial_kb,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filter_condition
        )
        
        return results
    
    # ========================================================================
    # TRANSACTIONS COLLECTION
    # ========================================================================
    
    def log_transaction(self, transaction: Dict[str, Any]):
        """Log user interaction/purchase"""
        point = PointStruct(
            id=hash(transaction['transaction_id']) & 0x7FFFFFFF,  # Convert string to positive int
            vector=transaction['embedding'],
            payload={
                'transaction_id': transaction['transaction_id'],
                'user_id': transaction['user_id'],
                'product_id': transaction['product_id'],
                'action': transaction['action'],
                'timestamp': transaction['timestamp'],
                'rating': transaction.get('rating'),
                'additional_data': transaction.get('additional_data', {})
            }
        )
        
        self.client.upsert(
            collection_name=settings.qdrant_collection_transactions,
            points=[point]
        )
    
    def get_user_transactions(
        self,
        user_id: str,
        action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get transaction history for a user"""
        filter_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        
        if action:
            filter_conditions.append(
                FieldCondition(key="action", match=MatchValue(value=action))
            )
        
        results = self.client.scroll(
            collection_name=settings.qdrant_collection_transactions,
            scroll_filter=Filter(must=filter_conditions),
            limit=100,
            with_vectors=False
        )
        
        return [point.payload for point in results[0]]
    
    def get_product_transactions(
        self,
        product_id: str,
        action: Optional[str] = None,
        min_rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get transactions for a specific product (for social proof)"""
        filter_conditions = [
            FieldCondition(key="product_id", match=MatchValue(value=product_id))
        ]
        
        if action:
            filter_conditions.append(
                FieldCondition(key="action", match=MatchValue(value=action))
            )
        
        if min_rating:
            filter_conditions.append(
                FieldCondition(key="rating", range=Range(gte=min_rating))
            )
        
        results = self.client.scroll(
            collection_name=settings.qdrant_collection_transactions,
            scroll_filter=Filter(must=filter_conditions),
            limit=1000,
            with_vectors=False
        )
        
        return [point.payload for point in results[0]]
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection"""
        return self.client.get_collection(collection_name)
    
    def count_points(self, collection_name: str) -> int:
        """Count number of points in a collection"""
        info = self.get_collection_info(collection_name)
        return info.points_count
    
    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Global instance
qdrant_manager = QdrantManager()

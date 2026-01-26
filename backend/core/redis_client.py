"""
Redis client for caching and Thompson Sampling state
"""
import redis
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis operations for caching and RL state"""
    
    def __init__(self):
        """Initialize Redis client"""
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        self.cache_ttl = settings.redis_cache_ttl
    
    # ========================================================================
    # CACHE OPERATIONS (Query Results)
    # ========================================================================
    
    def generate_cache_key(self, query: str, user_id: str) -> str:
        """
        Generate cache key from query and user ID
        
        Format: search:{query_hash}:{user_id}
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
        return f"search:{query_hash}:{user_id}"
    
    def get_cached_search(self, query: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached search results
        
        Returns:
            Cached response dict or None if not found
        """
        cache_key = self.generate_cache_key(query, user_id)
        
        try:
            cached_data = self.client.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for key: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache MISS for key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving cache: {e}")
            return None
    
    def cache_search_results(
        self,
        query: str,
        user_id: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache search results with TTL
        
        Args:
            query: Original search query
            user_id: User identifier
            response: Complete search response to cache
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        cache_key = self.generate_cache_key(query, user_id)
        ttl = ttl or self.cache_ttl
        
        try:
            self.client.setex(
                cache_key,
                timedelta(seconds=ttl),
                json.dumps(response)
            )
            logger.info(f"Cached response for key: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error caching results: {e}")
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        pattern = f"search:*:{user_id}"
        keys = self.client.keys(pattern)
        
        if keys:
            self.client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        info = self.client.info('stats')
        
        # Calculate hit rate
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0
        
        return {
            'hits': hits,
            'misses': misses,
            'hit_rate': hit_rate,
            'total_keys': self.client.dbsize()
        }
    
    # ========================================================================
    # THOMPSON SAMPLING STATE
    # ========================================================================
    
    def get_thompson_params(self, product_id: str) -> Dict[str, float]:
        """
        Get Thompson Sampling parameters (α, β) for a product
        
        Returns:
            {'alpha': float, 'beta': float}
        """
        key = f"thompson:{product_id}"
        
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            else:
                # Initialize with default values
                return {
                    'alpha': settings.thompson_alpha_init,
                    'beta': settings.thompson_beta_init
                }
        except Exception as e:
            logger.error(f"Error getting Thompson params for {product_id}: {e}")
            return {
                'alpha': settings.thompson_alpha_init,
                'beta': settings.thompson_beta_init
            }
    
    def update_thompson_params(
        self,
        product_id: str,
        signal_weight: float
    ):
        """
        Update Thompson Sampling parameters based on user action
        
        Args:
            product_id: Product identifier
            signal_weight: Signal weight (+1.0 to -1.0)
        """
        key = f"thompson:{product_id}"
        
        try:
            # Get current parameters
            params = self.get_thompson_params(product_id)
            alpha = params['alpha']
            beta = params['beta']
            
            # Update based on signal
            if signal_weight > 0:
                alpha += signal_weight
            else:
                beta += abs(signal_weight)
            
            # Save updated parameters (permanent, no TTL)
            updated_params = {
                'alpha': alpha,
                'beta': beta,
                'last_updated': str(timedelta(seconds=0))  # Will be replaced with actual time
            }
            
            self.client.set(key, json.dumps(updated_params))
            
            logger.info(
                f"Updated Thompson params for {product_id}: "
                f"α={alpha:.2f}, β={beta:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error updating Thompson params: {e}")
    
    def get_all_thompson_params(self) -> Dict[str, Dict[str, float]]:
        """Get Thompson parameters for all products"""
        pattern = "thompson:*"
        keys = self.client.keys(pattern)
        
        results = {}
        for key in keys:
            product_id = key.split(':')[1]
            data = self.client.get(key)
            if data:
                results[product_id] = json.loads(data)
        
        return results
    
    def get_thompson_stats(self) -> Dict[str, Any]:
        """Get overall Thompson Sampling statistics"""
        all_params = self.get_all_thompson_params()
        
        if not all_params:
            return {
                'products_tracked': 0,
                'total_products': 0,
                'avg_alpha': 0,
                'avg_beta': 0,
                'avg_conversion': 0
            }
        
        alphas = [p['alpha'] for p in all_params.values()]
        betas = [p['beta'] for p in all_params.values()]
        conversions = [
            a / (a + b) for a, b in zip(alphas, betas)
        ]
        
        return {
            'products_tracked': len(all_params),
            'total_products': len(all_params),
            'avg_alpha': sum(alphas) / len(alphas),
            'avg_beta': sum(betas) / len(betas),
            'avg_conversion': sum(conversions) / len(conversions)
        }
    
    # ========================================================================
    # METRICS & MONITORING
    # ========================================================================
    
    def increment_counter(self, key: str, amount: int = 1):
        """Increment a counter (for tracking events)"""
        self.client.incr(key, amount)
    
    def get_counter(self, key: str) -> int:
        """Get counter value"""
        value = self.client.get(key)
        return int(value) if value else 0
    
    def set_metric(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a metric value"""
        if ttl:
            self.client.setex(key, timedelta(seconds=ttl), json.dumps(value))
        else:
            self.client.set(key, json.dumps(value))
    
    def get_metric(self, key: str) -> Optional[Any]:
        """Get metric value"""
        value = self.client.get(key)
        return json.loads(value) if value else None
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def flush_all(self):
        """Clear all data (USE WITH CAUTION!)"""
        self.client.flushdb()
        logger.warning("Flushed all Redis data")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get Redis memory usage"""
        info = self.client.info('memory')
        return {
            'used_memory': info.get('used_memory_human'),
            'used_memory_peak': info.get('used_memory_peak_human'),
            'maxmemory': info.get('maxmemory_human')
        }


# Global instance
redis_manager = RedisManager()

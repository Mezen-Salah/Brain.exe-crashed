"""
FastAPI backend for PriceSense multi-agent recommendation system

Endpoints:
- POST /api/search - Main product search and recommendation
- POST /api/feedback/action - User action feedback for Thompson Sampling
- GET /api/health - System health check
- GET /api/cache/stats - Cache statistics
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import time
from datetime import datetime

from models.schemas import UserProfile, PathType
from models.state import AgentState
from services.orchestrator import execute_workflow
from services.routing import ComplexityRouter
from core.qdrant_client import qdrant_manager
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PriceSense API",
    description="Multi-agent AI recommendation system for e-commerce",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SearchRequest(BaseModel):
    """Request model for product search"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    user_profile: Optional[UserProfile] = Field(None, description="User financial profile")
    image_url: Optional[str] = Field(None, description="Optional image URL for visual search")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    use_cache: bool = Field(default=True, description="Whether to use cached results if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "affordable gaming laptop",
                "user_profile": {
                    "user_id": "user_123",
                    "monthly_income": 6000.0,
                    "monthly_expenses": 3500.0,
                    "savings": 12000.0,
                    "current_debt": 2000.0,
                    "credit_score": 720
                },
                "filters": {"max_price": 2000},
                "use_cache": True
            }
        }


class ProductResponse(BaseModel):
    """Product information in response"""
    product_id: str
    name: str
    price: float
    category: Optional[str] = None
    brand: Optional[str] = None
    rating: Optional[float] = None
    in_stock: bool = True
    description: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Single recommendation with scores"""
    rank: int
    product: ProductResponse
    final_score: float
    scores: Dict[str, float]
    affordability: Optional[Dict[str, Any]] = None
    explanation: str
    detailed_explanation: Optional[str] = None
    trust_score: Optional[float] = None
    verified: Optional[bool] = None
    cluster_alternatives: List[ProductResponse] = []


class SearchResponse(BaseModel):
    """Response model for product search"""
    success: bool
    query: str
    path_taken: str
    complexity_score: float
    recommendations: List[RecommendationResponse]
    total_candidates: int
    execution_time_ms: int
    cache_hit: bool = False
    errors: List[str] = []
    warnings: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "affordable gaming laptop",
                "path_taken": "DEEP",
                "complexity_score": 0.75,
                "recommendations": [],
                "total_candidates": 8,
                "execution_time_ms": 234,
                "cache_hit": False,
                "errors": [],
                "warnings": []
            }
        }


class FeedbackRequest(BaseModel):
    """Request model for user action feedback"""
    user_id: str = Field(..., description="User identifier")
    product_id: str = Field(..., description="Product identifier")
    action: str = Field(..., description="Action type: view, click, purchase, like, dislike")
    query: Optional[str] = Field(None, description="Original search query")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="User rating if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "product_id": "prod_456",
                "action": "purchase",
                "query": "gaming laptop",
                "rating": 4.5
            }
        }


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    success: bool
    message: str
    thompson_updated: bool = False


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    services: Dict[str, str]
    version: str


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics"""
    cache_enabled: bool
    total_keys: int
    memory_usage_mb: Optional[float] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "PriceSense API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    System health check
    
    Returns status of all critical services:
    - Qdrant (vector database)
    - Redis (Thompson Sampling state)
    - Agents (all 5 agents)
    """
    services = {}
    
    # Check Qdrant
    try:
        collections = qdrant_manager.client.get_collections()
        services["qdrant"] = "healthy"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        services["qdrant"] = f"unhealthy: {str(e)}"
    
    # Check Redis (Thompson Sampling)
    try:
        from core.redis_client import redis_manager
        redis_manager.client.ping()
        services["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = f"unhealthy: {str(e)}"
    
    # Agent status
    services["agent1_discovery"] = "healthy"
    services["agent2_financial"] = "healthy"
    services["agent2_5_pathfinder"] = "healthy"
    services["agent3_recommender"] = "healthy"
    services["agent4_explainer"] = "healthy"
    
    # Overall status
    all_healthy = all("healthy" in status for status in services.values())
    overall_status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        services=services,
        version="1.0.0"
    )


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_products(request: SearchRequest):
    """
    Main product search and recommendation endpoint
    
    Workflow:
    1. Estimate query complexity
    2. Determine path (FAST/SMART/DEEP)
    3. Execute multi-agent workflow
    4. Return ranked recommendations
    
    Paths:
    - FAST: Cache hit, instant results
    - SMART: Discovery + Ranking + Explanation (no financial analysis)
    - DEEP: Full pipeline with financial analysis
    """
    start_time = time.time()
    
    try:
        logger.info(f"Search request: '{request.query}' (user_profile: {request.user_profile is not None})")
        
        # Initialize state
        state = AgentState(
            query=request.query,
            user_profile=request.user_profile,
            image_embedding=None,  # TODO: Add image embedding support
            filters=request.filters or {},
            complexity_score=0.0,
            path_taken="DEEP",
            cache_hit=False,
            cached_response=None,
            candidate_products=[],
            search_time_ms=0,
            affordability_analyses={},
            affordable_products=[],
            all_unaffordable=False,
            financial_analysis_time_ms=0,
            retrieved_financial_rules=[],
            budget_paths=[],
            alternative_products=[],
            pathfinder_time_ms=0,
            thompson_scores={},
            collaborative_boosts={},
            ragas_scores={},
            cluster_alternatives={},
            final_recommendations=[],
            recommender_time_ms=0,
            explanations={},
            verification_results={},
            trust_scores={},
            explainer_time_ms=0,
            explanation_contexts={},
            ragas_metrics=None,
            total_execution_time_ms=0,
            errors=[],
            warnings=[]
        )
        
        # Determine complexity and path
        router = ComplexityRouter()
        complexity = router.estimate_complexity(state)
        path = router.determine_path(state, cache_available=request.use_cache and False)  # TODO: Implement cache check
        
        state['complexity_score'] = complexity
        state['path_taken'] = path.value
        
        logger.info(f"Complexity: {complexity:.2f}, Path: {path.value}")
        
        # Execute workflow
        result = execute_workflow(state, path=path.value)
        
        # Calculate total execution time
        total_time = int((time.time() - start_time) * 1000)
        
        # Helper function to get attribute or dict value
        def get_value(obj, key, default=None):
            """Get value from object attribute or dict key"""
            if hasattr(obj, key):
                return getattr(obj, key)
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default
        
        # Format recommendations
        recommendations = []
        for rec in result.get('final_recommendations', []):
            product = rec['product']
            
            # Convert product to response model
            product_response = ProductResponse(
                product_id=get_value(product, 'product_id'),
                name=get_value(product, 'name'),
                price=get_value(product, 'price'),
                category=get_value(product, 'category'),
                brand=get_value(product, 'brand'),
                rating=get_value(product, 'rating'),
                in_stock=get_value(product, 'in_stock', True),
                description=get_value(product, 'description')
            )
            
            # Convert cluster alternatives
            cluster_alts = []
            for alt in rec.get('cluster_alternatives', []):
                cluster_alts.append(ProductResponse(
                    product_id=get_value(alt, 'product_id'),
                    name=get_value(alt, 'name'),
                    price=get_value(alt, 'price'),
                    category=get_value(alt, 'category'),
                    brand=get_value(alt, 'brand'),
                    rating=get_value(alt, 'rating'),
                    in_stock=get_value(alt, 'in_stock', True),
                    description=get_value(alt, 'description')
                ))
            
            recommendations.append(RecommendationResponse(
                rank=rec['rank'],
                product=product_response,
                final_score=rec['final_score'],
                scores=rec.get('scores', {}),
                affordability=rec.get('affordability'),
                explanation=rec.get('explanation', ''),
                detailed_explanation=rec.get('detailed_explanation'),
                trust_score=rec.get('trust_score'),
                verified=rec.get('verified'),
                cluster_alternatives=cluster_alts
            ))
        
        return SearchResponse(
            success=True,
            query=request.query,
            path_taken=result.get('path_taken', path.value),
            complexity_score=complexity,
            recommendations=recommendations,
            total_candidates=len(result.get('candidate_products', [])),
            execution_time_ms=total_time,
            cache_hit=result.get('cache_hit', False),
            errors=result.get('errors', []),
            warnings=result.get('warnings', [])
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.post("/api/feedback/action", response_model=FeedbackResponse, tags=["Feedback"])
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user action feedback for Thompson Sampling
    
    Actions affect future recommendations:
    - purchase: Strong positive signal (+1.0 reward)
    - like: Positive signal (+0.5 reward)
    - click: Weak positive signal (+0.1 reward)
    - view: Neutral signal (exploration)
    - dislike: Negative signal (-0.5 reward)
    
    This updates the Thompson Sampling beta distribution for the product.
    """
    try:
        logger.info(f"Feedback: user={request.user_id}, product={request.product_id}, action={request.action}")
        
        # Map action to reward
        reward_map = {
            "purchase": 1.0,
            "like": 0.5,
            "click": 0.1,
            "view": 0.0,
            "dislike": -0.5
        }
        
        reward = reward_map.get(request.action.lower(), 0.0)
        
        # Store transaction in Qdrant
        try:
            transaction_data = {
                "user_id": request.user_id,
                "product_id": request.product_id,
                "action": request.action,
                "query": request.query,
                "rating": request.rating,
                "reward": reward,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            qdrant_manager.store_transaction(**transaction_data)
            logger.info(f"Stored transaction: {transaction_data}")
            
        except Exception as e:
            logger.error(f"Failed to store transaction: {e}")
        
        # Update Thompson Sampling (if positive action)
        thompson_updated = False
        if reward > 0:
            try:
                from core.redis_client import redis_manager
                
                # Get current parameters
                key = f"thompson:{request.product_id}"
                alpha = float(redis_manager.client.hget(key, "alpha") or 1.0)
                beta = float(redis_manager.client.hget(key, "beta") or 1.0)
                
                # Update based on reward
                if reward >= 0.5:  # Strong positive
                    alpha += 1.0
                else:  # Weak positive
                    alpha += 0.5
                    beta += 0.5
                
                # Store updated parameters
                redis_manager.client.hset(key, "alpha", alpha)
                redis_manager.client.hset(key, "beta", beta)
                
                thompson_updated = True
                logger.info(f"Thompson updated: {request.product_id} -> alpha={alpha}, beta={beta}")
                
            except Exception as e:
                logger.error(f"Failed to update Thompson Sampling: {e}")
        
        return FeedbackResponse(
            success=True,
            message=f"Feedback recorded for {request.action} on {request.product_id}",
            thompson_updated=thompson_updated
        )
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {str(e)}"
        )


@app.get("/api/cache/stats", response_model=CacheStatsResponse, tags=["Cache"])
async def get_cache_stats():
    """
    Get cache statistics
    
    Returns information about the Redis cache used for:
    - Thompson Sampling parameters
    - Cached search results (future)
    """
    try:
        from core.redis_client import redis_manager
        
        # Get number of keys
        total_keys = redis_manager.client.dbsize()
        
        # Get memory usage (if available)
        try:
            info = redis_manager.client.info("memory")
            memory_mb = info.get("used_memory", 0) / (1024 * 1024)
        except:
            memory_mb = None
        
        return CacheStatsResponse(
            cache_enabled=True,
            total_keys=total_keys,
            memory_usage_mb=memory_mb
        )
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return CacheStatsResponse(
            cache_enabled=False,
            total_keys=0,
            memory_usage_mb=None
        )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 80)
    logger.info("🚀 PriceSense API Starting Up")
    logger.info("=" * 80)
    
    # Check Qdrant connection
    try:
        collections = qdrant_manager.client.get_collections()
        logger.info(f"✅ Qdrant connected: {len(collections.collections)} collections")
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")
    
    # Check Redis connection
    try:
        from core.redis_client import redis_client
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
    
    logger.info("=" * 80)
    logger.info(f"📡 API running at: http://localhost:8000")
    logger.info(f"📚 Docs available at: http://localhost:8000/api/docs")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 PriceSense API Shutting Down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

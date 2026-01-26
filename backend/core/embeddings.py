"""
CLIP embeddings for multimodal (text + image) search
"""
import torch
import clip
from PIL import Image
import io
import base64
import logging
from typing import List, Optional, Union
import numpy as np
from core.config import settings

logger = logging.getLogger(__name__)


class CLIPEmbedder:
    """
    Handles text and image embeddings using CLIP ViT-B/32
    Produces 512-dimensional vectors
    """
    
    def __init__(self):
        """Initialize CLIP model"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading CLIP model on device: {self.device}")
        
        # Load CLIP ViT-B/32 (512-dimensional embeddings)
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.model.eval()  # Set to evaluation mode
        
        logger.info("CLIP model loaded successfully")
    
    # ========================================================================
    # TEXT EMBEDDINGS
    # ========================================================================
    
    def encode_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Convert text to 512-dimensional embedding
        
        Args:
            text: Single string or list of strings
            
        Returns:
            numpy array of shape (n, 512) for n texts
        """
        if isinstance(text, str):
            text = [text]
        
        with torch.no_grad():
            # Tokenize text
            tokens = clip.tokenize(text, truncate=True).to(self.device)
            
            # Generate embeddings
            embeddings = self.model.encode_text(tokens)
            
            # Normalize embeddings (for cosine similarity)
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            
            # Convert to numpy
            embeddings_np = embeddings.cpu().numpy()
        
        logger.debug(f"Encoded {len(text)} text(s) to embeddings of shape {embeddings_np.shape}")
        return embeddings_np
    
    def encode_query(self, query: str) -> List[float]:
        """
        Encode search query to embedding
        
        Args:
            query: Search query string
            
        Returns:
            512-dimensional embedding as list
        """
        embedding = self.encode_text(query)[0]
        return embedding.tolist()
    
    # ========================================================================
    # IMAGE EMBEDDINGS
    # ========================================================================
    
    def encode_image(self, image: Union[Image.Image, List[Image.Image]]) -> np.ndarray:
        """
        Convert image(s) to 512-dimensional embedding
        
        Args:
            image: PIL Image or list of PIL Images
            
        Returns:
            numpy array of shape (n, 512) for n images
        """
        if isinstance(image, Image.Image):
            image = [image]
        
        with torch.no_grad():
            # Preprocess images
            image_tensors = torch.stack([
                self.preprocess(img) for img in image
            ]).to(self.device)
            
            # Generate embeddings
            embeddings = self.model.encode_image(image_tensors)
            
            # Normalize embeddings
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
            
            # Convert to numpy
            embeddings_np = embeddings.cpu().numpy()
        
        logger.debug(f"Encoded {len(image)} image(s) to embeddings of shape {embeddings_np.shape}")
        return embeddings_np
    
    def encode_image_from_base64(self, base64_str: str) -> List[float]:
        """
        Encode image from base64 string
        
        Args:
            base64_str: Base64 encoded image
            
        Returns:
            512-dimensional embedding as list
        """
        try:
            # Decode base64 to image
            image_bytes = base64.b64decode(base64_str)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Encode image
            embedding = self.encode_image(image)[0]
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error encoding image from base64: {e}")
            raise ValueError(f"Invalid image data: {e}")
    
    # ========================================================================
    # MULTIMODAL (TEXT + IMAGE) EMBEDDINGS
    # ========================================================================
    
    def encode_multimodal(
        self,
        text: str,
        image_base64: Optional[str] = None,
        text_weight: float = 0.7,
        image_weight: float = 0.3
    ) -> List[float]:
        """
        Combine text and image embeddings with weighted average
        
        Args:
            text: Text query
            image_base64: Optional base64 encoded image
            text_weight: Weight for text embedding (default 0.7)
            image_weight: Weight for image embedding (default 0.3)
            
        Returns:
            512-dimensional combined embedding
        """
        # Encode text
        text_embedding = self.encode_text(text)[0]
        
        if image_base64:
            # Encode image
            image_embedding = np.array(self.encode_image_from_base64(image_base64))
            
            # Weighted combination
            combined = (text_weight * text_embedding + image_weight * image_embedding)
            
            # Normalize
            combined = combined / np.linalg.norm(combined)
            
            logger.info(f"Created multimodal embedding (text: {text_weight}, image: {image_weight})")
            return combined.tolist()
        else:
            # Text only
            return text_embedding.tolist()
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    def batch_encode_products(self, products: List[dict]) -> List[dict]:
        """
        Batch encode product descriptions
        
        Args:
            products: List of product dicts with 'description' field
            
        Returns:
            Same products with 'embedding' field added
        """
        descriptions = [p['description'] for p in products]
        embeddings = self.encode_text(descriptions)
        
        for product, embedding in zip(products, embeddings):
            product['embedding'] = embedding.tolist()
        
        logger.info(f"Batch encoded {len(products)} products")
        return products
    
    # ========================================================================
    # SIMILARITY CALCULATION
    # ========================================================================
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score between 0 and 1
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)


# Global instance
clip_embedder = CLIPEmbedder()

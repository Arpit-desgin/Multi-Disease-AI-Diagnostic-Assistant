"""
Embedding service for generating text embeddings using sentence-transformers.
"""

from typing import List
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    A wrapper class for generating embeddings using sentence-transformers.
    
    Uses the "all-MiniLM-L6-v2" model which is a lightweight, efficient model
    suitable for semantic search and RAG applications.
    """
    
    def __init__(self):
        """
        Initialize the embedding model.
        
        Loads the pre-trained sentence-transformer model.
        Model is automatically cached after first download.
        """
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The input text to embed
            
        Returns:
            A list of floats representing the embedding vector
        """
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors, each as a list of floats
        """
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()

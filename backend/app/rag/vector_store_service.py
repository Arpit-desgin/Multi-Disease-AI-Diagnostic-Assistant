"""
Vector store service using ChromaDB for semantic search and RAG operations.

Uses the modern ChromaDB API (0.4.0+) with PersistentClient for persistent storage.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb

from constants import CHROMA_DB_PATH

logger = logging.getLogger("app.rag.vector_store")


class VectorStore:
    """
    A vector store service for managing embeddings and semantic search using ChromaDB.
    
    Supports multiple disease-specific collections with persistent local storage.
    Uses the modern ChromaDB PersistentClient API for compatibility with ChromaDB 0.4.0+.
    """
    
    # Standard disease collections
    # Maps medical conditions to their respective vector store collections
    COLLECTIONS = [
        "dermatology",           # Skin diseases
        "lung_cancer",           # Respiratory/lung diseases
        "breast_cancer",         # Breast-related diseases
        "diabetic_retinopathy",  # Eye diseases (DR and related)
        "general_diseases"       # Miscellaneous/general diseases
    ]
    
    def __init__(self, persist_directory: str | None = None):
        """
        Initialize the vector store with persistent storage.
        
        Uses ChromaDB's PersistentClient which manages data persistence automatically.
        Data is stored locally on disk and persists across server restarts.
        
        Args:
            persist_directory: Path where ChromaDB data will be stored locally.
                              Defaults to CHROMA_DB_PATH from constants
        """
        # Use global constant if no path provided
        if persist_directory is None:
            persist_directory = str(CHROMA_DB_PATH)
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        logger.info(f"[VECTOR_STORE] Initializing with persist_directory: {persist_directory}")
        
        # FIX: Use modern PersistentClient instead of deprecated Client + Settings
        # PersistentClient automatically handles:
        # - Data persistence to disk
        # - Collection management
        # - Index persistence
        # - Thread-safe operations
        try:
            # Try new API (chromadb >= 0.4.0)
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                anonymized_telemetry=False
            )
            logger.info(f"[VECTOR_STORE] Using modern PersistentClient API")
        except TypeError:
            # Fallback for older versions: use Client with is_persistent=True
            from chromadb.config import Settings
            settings = Settings(
                is_persistent=True,
                persist_directory=persist_directory,
                anonymized_telemetry=False
            )
            self.client = chromadb.Client(settings)
            logger.warning(f"[VECTOR_STORE] Using legacy Client API (consider upgrading ChromaDB)")
        
        # Initialize or get collections
        self.collections = {}
        logger.info(f"[VECTOR_STORE] Initializing {len(self.COLLECTIONS)} collections...")
        
        for collection_name in self.COLLECTIONS:
            # Get or create collection with cosine similarity metric
            self.collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            count = self.collections[collection_name].count()
            logger.info(f"[VECTOR_STORE]   ✓ '{collection_name}': {count} documents")
        
        logger.info(f"[VECTOR_STORE] ✅ Vector store ready (fully offline, local embeddings)")
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add documents with embeddings to a collection.
        
        Args:
            collection_name: Name of the collection (must be one of COLLECTIONS)
            documents: List of documents, each with:
                      - text: str - the document content
                      - metadata: Dict - containing disease type, source, etc.
            embeddings: List of embedding vectors (each as list of floats)
                       Must be same length as documents list
            
        Raises:
            ValueError: If collection_name not in COLLECTIONS or length mismatch
        """
        if collection_name not in self.COLLECTIONS:
            raise ValueError(f"Collection '{collection_name}' not supported. "
                           f"Must be one of: {self.COLLECTIONS}")
        
        if len(documents) != len(embeddings):
            raise ValueError(f"Number of documents ({len(documents)}) must match "
                           f"number of embeddings ({len(embeddings)})")
        
        collection = self.collections[collection_name]
        
        logger.info(f"[VECTOR_STORE] Adding {len(documents)} documents to '{collection_name}'")
        
        # Prepare data for ChromaDB
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = f"{collection_name}_{i}_{hash(str(doc)) % 10000}"
            ids.append(doc_id)
            texts.append(doc["text"])
            metadatas.append(doc.get("metadata", {}))
        
        # Add to collection
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"[VECTOR_STORE] ✅ Successfully added {len(ids)} documents to '{collection_name}'")
        except Exception as e:
            logger.error(f"[VECTOR_STORE] ❌ Error adding documents to '{collection_name}': {str(e)}")
            raise
    
    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            collection_name: Name of the collection to query
            query_embedding: Query embedding vector (list of floats)
            top_k: Number of top results to return. Defaults to 5
            
        Returns:
            Dictionary containing:
            - ids: List of document IDs
            - documents: List of document texts
            - distances: List of distance scores (lower is more similar)
            - metadatas: List of metadata dictionaries
            
        Raises:
            ValueError: If collection_name not in COLLECTIONS
        """
        if collection_name not in self.COLLECTIONS:
            raise ValueError(f"Collection '{collection_name}' not supported. "
                           f"Must be one of: {self.COLLECTIONS}")
        
        collection = self.collections[collection_name]
        
        logger.debug(f"[VECTOR_STORE] Querying collection '{collection_name}' (top_k={top_k})")
        
        # Query the collection
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            logger.debug(f"[VECTOR_STORE] Query returned {len(results['ids'][0]) if results['ids'] else 0} results")
            
            # Flatten results (ChromaDB returns nested lists for batch queries)
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else []
            }
        except Exception as e:
            logger.error(f"[VECTOR_STORE] Error querying collection '{collection_name}': {str(e)}")
            raise
    
    def persist(self) -> None:
        """
        Explicitly persist data to disk.
        
        Note: ChromaDB's PersistentClient automatically persists changes to disk.
        This method is provided for backward compatibility and explicit control.
        It's generally not needed but can be called for safety before critical operations.
        """
        # PersistentClient handles persistence automatically
        # Only old Client API required manual persist() calls
        try:
            # Try to call persist if available (older versions)
            if hasattr(self.client, 'persist'):
                self.client.persist()
        except Exception:
            # PersistentClient doesn't have persist() method, which is fine
            # Data is persisted automatically to disk
            pass
    
    def get_collection_count(self, collection_name: str) -> int:
        """
        Get the number of documents in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Count of documents in the collection
        """
        if collection_name not in self.COLLECTIONS:
            raise ValueError(f"Collection '{collection_name}' not supported. "
                           f"Must be one of: {self.COLLECTIONS}")
        
        return self.collections[collection_name].count()
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete all documents from a collection.
        
        Args:
            collection_name: Name of the collection to clear
        """
        if collection_name not in self.COLLECTIONS:
            raise ValueError(f"Collection '{collection_name}' not supported. "
                           f"Must be one of: {self.COLLECTIONS}")
        
        self.client.delete_collection(name=collection_name)
        # Recreate empty collection
        self.collections[collection_name] = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

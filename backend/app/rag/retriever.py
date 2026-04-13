"""
Retriever module for fetching relevant documents from the vector store.

Handles semantic search across disease-specific collections with flexible
filtering by disease type, including fallback retrieval strategies.
"""

from typing import List, Dict, Any, Optional
import logging

from embedding_service import EmbeddingModel
from vector_store_service import VectorStore
from constants import CHROMA_DB_PATH

logger = logging.getLogger("app.rag.retriever")


class Retriever:
    """
    Retriever for semantic search across the vector store.
    
    Converts queries to embeddings and searches disease-specific collections
    or all collections if no disease type is specified.
    """
    
    def __init__(self, persist_directory: str | None = None):
        """
        Initialize the retriever.
        
        Args:
            persist_directory: Path to the ChromaDB persistent storage
                              Defaults to CHROMA_DB_PATH from constants
        """
        if persist_directory is None:
            persist_directory = str(CHROMA_DB_PATH)
        
        logger.info(f"[RETRIEVER] Initializing with persist_directory: {persist_directory}")
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore(persist_directory=persist_directory)
    
    def retrieve(
        self,
        query: str,
        disease_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query with fallback strategies.
        
        Converts the query to an embedding and searches either a specific
        disease collection or all collections for the most relevant documents.
        
        Includes fallback logic: if no results found with disease_type filter,
        retries without filter.
        
        Args:
            query: The search query string
            disease_type: Optional specific disease collection to search
                         (dermatology, lung_cancer, breast_cancer, 
                          diabetic_retinopathy, general_diseases)
                         If None, searches all collections
            top_k: Number of results to return per collection (default 5)
            
        Returns:
            List of results, each containing:
            - id: Document ID
            - text: Document text
            - distance: Similarity distance (lower is more similar)
            - metadata: Document metadata (disease_type, source, chunk_size)
            - collection: Which collection this result came from
            
        Raises:
            ValueError: If disease_type is not valid
        """
        if not query or not query.strip():
            logger.warning("[RETRIEVER] Empty query received")
            return []
        
        logger.info(f"[RETRIEVER] Query: '{query[:100]}' | Disease type: {disease_type}")
        
        # Generate embedding for query
        query_embedding = self.embedding_model.embed_text(query)
        logger.info(f"[RETRIEVER] Generated query embedding (dimension: {len(query_embedding)})")
        
        # Determine which collections to search
        if disease_type:
            if disease_type not in self.vector_store.COLLECTIONS:
                raise ValueError(
                    f"Invalid disease_type: '{disease_type}'. "
                    f"Must be one of: {self.vector_store.COLLECTIONS}"
                )
            collections_to_search = [disease_type]
            logger.info(f"[RETRIEVER] Searching specific collection: {disease_type}")
        else:
            collections_to_search = self.vector_store.COLLECTIONS
            logger.info(f"[RETRIEVER] Searching all {len(collections_to_search)} collections")
        
        # Collect results from all relevant collections
        all_results = []
        
        for collection_name in collections_to_search:
            try:
                collection_count = self.vector_store.get_collection_count(collection_name)
                logger.info(f"[RETRIEVER] Collection '{collection_name}' has {collection_count} documents")
                
                if collection_count == 0:
                    logger.warning(f"[RETRIEVER] Collection '{collection_name}' is empty - skipping")
                    continue
                
                # Query the collection
                results = self.vector_store.query(
                    collection_name=collection_name,
                    query_embedding=query_embedding,
                    top_k=top_k
                )
                
                logger.info(f"[RETRIEVER] Found {len(results['ids'])} results in '{collection_name}'")
                
                # Format results
                for i in range(len(results["ids"])):
                    result = {
                        "id": results["ids"][i],
                        "text": results["documents"][i],
                        "distance": results["distances"][i],
                        "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
                        "collection": collection_name
                    }
                    all_results.append(result)
                    logger.debug(f"[RETRIEVER]   Result {i+1}: distance={result['distance']:.4f}, length={len(result['text'])}")
            
            except Exception as e:
                logger.error(f"[RETRIEVER] Error querying collection '{collection_name}': {str(e)}", exc_info=True)
                continue
        
        logger.info(f"[RETRIEVER] Total results before filtering: {len(all_results)}")
        
        # FALLBACK: If no results with disease_type filter, retry without disease type
        if not all_results and disease_type:
            logger.warning(f"[RETRIEVER] ⚠️  No results found with disease_type='{disease_type}'")
            logger.info(f"[RETRIEVER] Attempting FALLBACK retrieval without disease type filter...")
            
            # Retry without disease type - search all collections
            for collection_name in self.vector_store.COLLECTIONS:
                try:
                    results = self.vector_store.query(
                        collection_name=collection_name,
                        query_embedding=query_embedding,
                        top_k=top_k
                    )
                    
                    logger.info(f"[RETRIEVER] FALLBACK: Found {len(results['ids'])} results in '{collection_name}'")
                    
                    for i in range(len(results["ids"])):
                        result = {
                            "id": results["ids"][i],
                            "text": results["documents"][i],
                            "distance": results["distances"][i],
                            "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
                            "collection": collection_name
                        }
                        all_results.append(result)
                
                except Exception as e:
                    logger.error(f"[RETRIEVER] FALLBACK error in '{collection_name}': {str(e)}")
                    continue
        
        # If searching multiple collections, sort by distance and return top_k overall
        if not disease_type and all_results:
            all_results = sorted(all_results, key=lambda x: x["distance"])
            all_results = all_results[:top_k]
            logger.info(f"[RETRIEVER] Sorted and limited results to top {min(top_k, len(all_results))}")
        elif all_results:
            all_results = sorted(all_results, key=lambda x: x["distance"])
            logger.info(f"[RETRIEVER] Sorted {len(all_results)} results by distance")
        
        if not all_results:
            logger.warning(f"[RETRIEVER] ⚠️  FINAL: No documents retrieved for query '{query[:50]}'")
        else:
            logger.info(f"[RETRIEVER] ✅ FINAL: Retrieved {len(all_results)} documents")
        
        return all_results
    
    def retrieve_by_disease(
        self,
        query: str,
        disease_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from a specific disease collection.
        
        Convenience method that enforces disease type selection.
        
        Args:
            query: The search query string
            disease_type: Disease collection to search (required)
            top_k: Number of results to return (default 5)
            
        Returns:
            List of relevant documents with metadata
            
        Raises:
            ValueError: If disease_type is not valid
        """
        return self.retrieve(query, disease_type=disease_type, top_k=top_k)
    
    def retrieve_all(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from all disease collections.
        
        Convenience method for searching across all collections.
        
        Args:
            query: The search query string
            top_k: Number of results to return (default 5)
            
        Returns:
            List of relevant documents from all collections, sorted by relevance
        """
        return self.retrieve(query, disease_type=None, top_k=top_k)
    
    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format retrieval results as readable text.
        
        Args:
            results: List of results from retrieve()
            
        Returns:
            Formatted string representation of results
        """
        if not results:
            return "No relevant documents found."
        
        output = f"Found {len(results)} relevant document(s):\n"
        output += "="*70 + "\n"
        
        for i, result in enumerate(results, 1):
            output += f"\n[{i}] {result['collection'].upper()}\n"
            output += f"    ID: {result['id']}\n"
            output += f"    Distance: {result['distance']:.4f}\n"
            output += f"    Source: {result['metadata'].get('source', 'Unknown')}\n"
            output += f"    Text: {result['text'][:200]}...\n" if len(result['text']) > 200 else f"    Text: {result['text']}\n"
        
        return output

"""
RAG (Retrieval-Augmented Generation) Pipeline for medical question answering.

Retrieves relevant documents and formats them into structured medical responses
using only local, offline processing - NO external API calls required.
"""

import logging
from typing import List, Dict, Any, Optional
import re
import sys
from pathlib import Path

from retriever import Retriever
from constants import CHROMA_DB_PATH

# Import Ollama service for LLM-based answer generation
try:
    from app.services.ollama_service import generate_answer as ollama_generate
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    def ollama_generate(*args, **kwargs):
        return {"answer": "", "error": "Ollama service not available", "fallback": True}

logger = logging.getLogger("app.rag.rag_pipeline")


class RAGPipeline:
    """
    Local RAG Pipeline for generating medical answers using retrieved context.
    
    Retrieves relevant documents and formats them into structured responses
    with Definition, Symptoms, Causes, and Treatment sections.
    
    Fully offline - no external API calls required.
    """
    
    def __init__(
        self,
        model: str = "local",
        temperature: float = 0.2,
        max_tokens: int = 500,
        api_key: Optional[str] = None,
        persist_directory: str | None = None
    ):
        """
        Initialize the local RAG pipeline.
        
        Args:
            model: Model name (unused, kept for compatibility, always "local")
            temperature: Temperature parameter (unused, kept for compatibility)
            max_tokens: Max length for responses (used for truncation)
            api_key: API key (unused, kept for compatibility)
            persist_directory: Path to ChromaDB persistent storage
                              Defaults to CHROMA_DB_PATH from constants
        """
        # Use global constant if no path provided
        if persist_directory is None:
            persist_directory = str(CHROMA_DB_PATH)
        
        self.model = "local"
        self.max_tokens = max_tokens
        self.persist_directory = persist_directory
        
        logger.info(f"[RAG] RAG pipeline initialized with local, offline embeddings")
        logger.info(f"[RAG] Using persist_directory: {persist_directory}")
        logger.info(f"[RAG] Using local embeddings (sentence-transformers: all-MiniLM-L6-v2)")
        logger.info(f"[RAG] No external API calls required - fully offline operation")
        
        # Initialize retriever (uses local SentenceTransformer embeddings)
        self.retriever = Retriever(persist_directory=persist_directory)
        
        # NEW: Auto-ingest documents if vector DB is empty
        self._auto_ingest_if_empty()
    
    def _auto_ingest_if_empty(self) -> None:
        """
        Check if vector store collections are empty and auto-ingest documents if needed.
        
        This ensures that if documents haven't been loaded yet, they are loaded automatically
        on first RAG pipeline initialization. Prevents the "0 documents" issue.
        """
        logger.info("[RAG] Checking if vector store needs auto-ingestion...")
        
        try:
            from vector_store_service import VectorStore
            
            vs = VectorStore(persist_directory=self.persist_directory)
            total_docs = sum(vs.get_collection_count(col) for col in vs.COLLECTIONS)
            
            logger.info(f"[RAG] Vector store status: {total_docs} documents indexed")
            
            if total_docs == 0:
                logger.warning("[RAG] ⚠️  Vector store is EMPTY - auto-ingesting documents...")
                
                try:
                    from ingest import build_index
                    
                    logger.info("[RAG] Starting auto-ingestion...")
                    stats = build_index(data_dir="Data", chunk_size=500, chunk_overlap=50)
                    
                    logger.info(f"[RAG] Auto-ingestion completed:")
                    logger.info(f"[RAG]   Files: {stats.get('files_processed', 0)}")
                    logger.info(f"[RAG]   Chunks: {stats.get('chunks_created', 0)}")
                    logger.info(f"[RAG]   Stored: {stats.get('documents_stored', 0)}")
                    
                    # Verify ingestion
                    new_total = sum(vs.get_collection_count(col) for col in vs.COLLECTIONS)
                    if new_total > 0:
                        logger.info(f"[RAG] ✅ Auto-ingestion SUCCESS: {new_total} documents now available")
                    else:
                        logger.warning(f"[RAG] ⚠️  Auto-ingestion completed but still 0 documents")
                        logger.warning("[RAG] → Check that Data/ folder contains .txt files")
                        logger.warning("[RAG] → Or run 'python ingest.py' manually")
                
                except Exception as e:
                    logger.error(f"[RAG] Auto-ingestion FAILED: {str(e)}")
                    logger.info("[RAG] → Run 'python ingest.py' from backend/app/rag/ directory manually")
            else:
                logger.info(f"[RAG] ✅ Vector store is ready with {total_docs} documents")
        
        except Exception as e:
            logger.error(f"[RAG] Auto-ingestion check failed: {str(e)}")
    
    def generate_answer(
        self,
        query: str,
        disease_type: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a medical answer for a query using local retrieval and formatting.
        
        Retrieves relevant documents and formats them into a structured response
        with Definition, Symptoms, Causes, and Treatment sections.
        
        Args:
            query: The medical question
            disease_type: Optional disease type to filter search
                         (dermatology, lung_cancer, breast_cancer, general_diseases)
            top_k: Number of documents to retrieve (default 5)
            
        Returns:
            Dictionary containing:
            - answer: Formatted response from retrieved documents
            - sources: List of source documents used (with metadata)
            - retrieved_count: Number of documents retrieved
            - model: Model used ("local")
            - error: Error message if any
        """
        if not query or not query.strip():
            logger.error("[RAG] Empty query received")
            return {
                "answer": "",
                "sources": [],
                "retrieved_count": 0,
                "model": "local",
                "error": "Query cannot be empty"
            }
        
        logger.info(f"[RAG] ============================================================")
        logger.info(f"[RAG] Processing RAG Query: '{query[:100]}'")
        logger.info(f"[RAG] Disease type: {disease_type}, Top-K: {top_k}")
        logger.info(f"[RAG] ============================================================")
        
        # Step 1: Retrieve relevant documents using local embeddings
        logger.info(f"[RAG] STEP 1: Retrieving documents...")
        retrieved_docs = self.retriever.retrieve(
            query=query,
            disease_type=disease_type,
            top_k=top_k
        )
        
        logger.info(f"[RAG] STEP 1 RESULT: {len(retrieved_docs)} documents retrieved (before filtering)")
        
        # Filter out irrelevant documents (e.g., "no_*" files)
        filtered_docs = []
        excluded_count = 0
        
        for doc in retrieved_docs:
            source = doc.get("metadata", {}).get("source", "").lower()
            
            # Exclude documents with "no_" prefix (e.g., "no_lung_cancer", "no_diabetes")
            if source.startswith("no_"):
                logger.debug(f"[RAG] ⊘ Excluding irrelevant document: {source}")
                excluded_count += 1
                continue
            
            # Exclude documents that are too short or empty
            text = doc.get("text", "").strip()
            if len(text) < 20:
                logger.debug(f"[RAG] ⊘ Excluding too-short document from {source}")
                excluded_count += 1
                continue
            
            filtered_docs.append(doc)
        
        if excluded_count > 0:
            logger.info(f"[RAG] Filtered out {excluded_count} irrelevant documents")
        
        if not filtered_docs:
            logger.warning(f"[RAG] ⚠️  FAILURE: No relevant documents after filtering for query: {query[:50]}")
            return {
                "answer": "No relevant medical information found in the database for this query.",
                "sources": [],
                "retrieved_count": 0,
                "model": "local",
                "error": "No documents retrieved"
            }
        
        # Log retrieved document details
        logger.info(f"[RAG] STEP 1 FINAL: {len(filtered_docs)} relevant documents")
        for i, doc in enumerate(filtered_docs, 1):
            source = doc.get("metadata", {}).get("source", "Unknown")
            distance = doc.get('distance', -1)
            logger.info(f"[RAG]   [{i}] {source} (distance: {distance:.4f})")
        
        logger.info(f"[RAG] STEP 2: Preparing context and calling LLM...")
        
        # Step 2: Combine and deduplicate  retrieved documents into context
        combined_context = self._deduplicate_and_combine_docs(filtered_docs)
        logger.info(f"[RAG] Final context: {len(combined_context)} characters from {len(filtered_docs)} documents")
        
        # Step 3: Use Ollama LLM to generate answer from context
        logger.info(f"[RAG] STEP 3: Generating answer with Ollama (model: mistral)...")
        
        llm_result = ollama_generate(
            question=query,
            context=combined_context,
            model="mistral",
            temperature=0.3,
            top_p=0.9
        )
        
        if llm_result.get("error"):
            logger.warning(f"[RAG] ⚠️  LLM generation failed: {llm_result['error']}")
            logger.warning(f"[RAG] → Falling back to document formatting...")
            answer = self._format_answer_from_documents(query, filtered_docs)
        else:
            answer = llm_result.get("answer", "")
            logger.info(f"[RAG] ✅ LLM generated response ({len(answer)} chars)")
        
        # Step 4: Extract and format sources (from filtered docs only)
        sources = self._format_sources(filtered_docs)
        
        logger.info(f"[RAG] STEP 4 RESULT: {len(sources)} sources identified")
        
        logger.info(f"[RAG] ✅ SUCCESS: Generated RAG response")
        logger.info(f"[RAG] ============================================================\n")
        
        # Step 5: Return structured response
        return {
            "answer": answer,
            "sources": sources,
            "retrieved_count": len(filtered_docs),
            "model": llm_result.get("model", "mistral"),
            "error": None
        }
    
    def _deduplicate_and_combine_docs(self, docs: List[Dict[str, Any]]) -> str:
        """
        Deduplicate and combine retrieved documents into a single context string.
        
        Removes duplicate text content and normalizes spacing.
        
        Args:
            docs: List of retrieved document dictionaries
            
        Returns:
            Combined, deduplicated context string
        """
        if not docs:
            return ""
        
        # Extract text and normalize
        seen_texts = set()
        combined_parts = []
        
        for doc in docs:
            text = doc.get("text", "").strip()
            
            if not text:
                continue
            
            # Normalize for deduplication check (lowercase, remove extra whitespace)
            normalized = " ".join(text.lower().split())
            
            # Only add if we haven't seen this exact content before
            if normalized not in seen_texts:
                combined_parts.append(text)
                seen_texts.add(normalized)
        
        # Join with space separator
        combined_context = " ".join(combined_parts)
        
        logger.debug(f"[RAG] Deduplication: {len(docs)} docs → {len(combined_parts)} unique chunks")
        
        return combined_context
    
    def _format_answer_from_documents(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Format a structured answer from retrieved documents (FALLBACK).
        
        This is used when Ollama is not available or fails.
        Organizes content into Definition, Symptoms, Causes, and Treatment sections.
        
        Args:
            query: The original query
            retrieved_docs: List of retrieved documents
            
        Returns:
            Formatted answer string with sections
        """
        if not retrieved_docs:
            return "No information available."
        
        # Combine all retrieved text
        combined_text = " ".join([doc.get("text", "") for doc in retrieved_docs])
        
        # Extract sections from combined text
        definition = self._extract_section(combined_text, "definition", 150)
        symptoms = self._extract_section(combined_text, "symptoms|signs|manifestations", 200)
        causes = self._extract_section(combined_text, "causes|etiology|risk factors", 150)
        treatment = self._extract_section(combined_text, "treatment|management|therapy", 200)
        
        # Build structured answer
        answer_parts = []
        
        # Add disease name from query if identifiable
        disease_name = self._extract_disease_name(query, retrieved_docs)
        if disease_name:
            answer_parts.append(f"**{disease_name}**\n")
        
        # Add definition
        if definition:
            answer_parts.append(f"**Definition:**\n{definition}\n")
        
        # Add symptoms
        if symptoms:
            answer_parts.append(f"**Symptoms:**\n{symptoms}\n")
        
        # Add causes
        if causes:
            answer_parts.append(f"**Causes:**\n{causes}\n")
        
        # Add treatment
        if treatment:
            answer_parts.append(f"**Treatment:**\n{treatment}\n")
        
        # Add source attribution
        if retrieved_docs:
            source_files = list(set([doc.get("metadata", {}).get("source", "Unknown") for doc in retrieved_docs]))
            sources_str = ", ".join([s.replace(".txt", "") for s in source_files[:3]])
            answer_parts.append(f"\n*Sources: {sources_str}*")
        
        # Add disclaimer
        answer_parts.append("\n\n**Disclaimer:** This information is educational only and should not replace professional medical advice. Please consult a qualified healthcare provider.")
        
        return "".join(answer_parts)
    
    def _extract_section(self, text: str, section_keywords: str, max_length: int = 150) -> str:
        """
        Extract a section from text based on keywords.
        
        Args:
            text: Full text to search
            section_keywords: Regex pattern for section keywords (e.g., "definition|overview")
            max_length: Maximum length of extracted text
            
        Returns:
            Extracted section text, truncated if necessary
        """
        # Try to find sentences containing the keywords
        sentences = re.split(r'[.!?]\s+', text)
        
        relevant_sentences = []
        for sentence in sentences:
            if re.search(section_keywords, sentence, re.IGNORECASE):
                relevant_sentences.append(sentence.strip())
            # Also include sentences immediately after a matching sentence
            elif relevant_sentences and len(" ".join(relevant_sentences)) < max_length:
                relevant_sentences.append(sentence.strip())
        
        # If no keyword match found, extract first few sentences as fallback
        if not relevant_sentences:
            relevant_sentences = [s.strip() for s in sentences[:2] if s.strip()]
        
        # Join and limit length
        result = " ".join(relevant_sentences)
        
        if len(result) > max_length:
            result = result[:max_length].rsplit(' ', 1)[0] + "..."
        
        return result.strip()
    
    def _extract_disease_name(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Extract disease name from query or document metadata.
        
        Args:
            query: User's query
            retrieved_docs: Retrieved documents
            
        Returns:
            Disease name if identifiable, empty string otherwise
        """
        # Try to get from document metadata
        for doc in retrieved_docs:
            metadata = doc.get("metadata", {})
            if "disease_name" in metadata:
                return metadata["disease_name"]
        
        # Try to extract from collection name
        if retrieved_docs:
            collection = retrieved_docs[0].get("collection", "").replace("_", " ").title()
            if collection and collection not in ["Unknown", "General Diseases"]:
                return collection
        
        return ""
    
    def _format_sources(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format source documents from retrieval results.
        
        Args:
            retrieved_docs: List of retrieved documents
            
        Returns:
            List of formatted source dictionaries
        """
        sources = []
        
        for doc in retrieved_docs:
            source = {
                "id": doc.get("id", ""),
                "collection": doc.get("collection", "unknown"),
                "source_file": doc.get("metadata", {}).get("source", "Unknown"),
                "relevance_score": 1 - doc.get("distance", 0),  # Convert distance to similarity
                "preview": doc.get("text", "")[:150] + "..."
            }
            sources.append(source)
        
        return sources
    
    def generate_answer_batch(
        self,
        queries: List[str],
        disease_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate answers for multiple queries using local processing.
        
        Args:
            queries: List of medical questions
            disease_type: Optional disease type to filter all searches
            top_k: Number of documents to retrieve per query
            
        Returns:
            List of answer dictionaries (same format as generate_answer)
        """
        results = []
        
        for query in queries:
            result = self.generate_answer(
                query=query,
                disease_type=disease_type,
                top_k=top_k
            )
            results.append(result)
        
        return results


def main():
    """Example usage of the local RAG pipeline."""
    # Initialize pipeline (no API key needed)
    try:
        pipeline = RAGPipeline()
        logger.info("✅ RAG pipeline initialized successfully (fully local, offline)")
    except Exception as e:
        logger.error(f"Error: {e}")
        return
    
    # Example queries
    example_queries = [
        "What are the symptoms of skin cancer?",
        "How is lung cancer diagnosed?"
    ]
    
    print("="*70)
    print("Local RAG Pipeline - Medical Question Answering (No API Required)")
    print("="*70)
    
    for query in example_queries:
        print(f"\nQuery: {query}")
        print("-"*70)
        
        result = pipeline.generate_answer(query)
        
        if result.get("error"):
            print(f"Error: {result['error']}")
            continue
        
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nRetrieved {result['retrieved_count']} relevant document(s)")
        print("\nSources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  [{i}] {source['source_file']} ({source['collection']})")
            print(f"       Relevance: {source['relevance_score']:.2%}")


if __name__ == "__main__":
    main()

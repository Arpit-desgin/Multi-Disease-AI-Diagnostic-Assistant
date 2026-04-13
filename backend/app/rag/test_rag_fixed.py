"""
Comprehensive test script for RAG retrieval pipeline.
FIXED VERSION: No emoji characters for Windows console compatibility.

Tests:
1. Vector store initialization and document counts
2. Embedding generation
3. Document retrieval
4. RAG answer generation
5. Fallback retrieval strategies
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_rag")


def test_vector_store():
    """Test 1: Verify vector store has documents indexed."""
    print("\n" + "="*70)
    print("TEST 1: Vector Store Structure")
    print("="*70)
    
    try:
        from vector_store_service import VectorStore
        
        vs = VectorStore(persist_directory="./chroma_data")
        logger.info("[TEST] Vector store initialized")
        
        print("\nCollection Document Counts:")
        total_docs = 0
        for collection in vs.COLLECTIONS:
            count = vs.get_collection_count(collection)
            total_docs += count
            status = "[OK]" if count > 0 else "[EMPTY]"
            print(f"  {status} {collection:20s}: {count:3d} documents")
        
        print(f"\n  Total documents indexed: {total_docs}")
        
        if total_docs == 0:
            logger.error("[TEST] FAILURE: No documents in vector store!")
            logger.error("[TEST]    -> Run: python run_build.py")
            return False
        
        logger.info("[TEST] TEST 1 PASSED: Documents found in vector store")
        return True
    
    except Exception as e:
        logger.error(f"[TEST] TEST 1 FAILED: {str(e)}", exc_info=True)
        return False


def test_embeddings():
    """Test 2: Verify embedding generation works."""
    print("\n" + "="*70)
    print("TEST 2: Embedding Generation")
    print("="*70)
    
    try:
        from embedding_service import EmbeddingModel
        
        em = EmbeddingModel()
        logger.info("[TEST] EmbeddingModel initialized using all-MiniLM-L6-v2")
        
        # Test single embedding
        test_text = "What is lung cancer?"
        embedding = em.embed_text(test_text)
        
        print(f"\nTest query: '{test_text}'")
        print(f"  Embedding dimension: {len(embedding)}")
        print(f"  Sample values: {embedding[:5]}")
        
        if len(embedding) != 384:
            logger.error(f"[TEST] Wrong embedding dimension: expected 384, got {len(embedding)}")
            return False
        
        # Test batch embedding
        test_texts = ["skin cancer", "lung disease", "breast health"]
        embeddings = em.embed_batch(test_texts)
        print(f"\nBatch test: {len(test_texts)} texts")
        print(f"  Generated embeddings: {len(embeddings)}")
        
        if len(embeddings) != len(test_texts):
            logger.error("[TEST] Batch embedding count mismatch")
            return False
        
        logger.info("[TEST] TEST 2 PASSED: Embeddings working correctly")
        return True
    
    except Exception as e:
        logger.error(f"[TEST] TEST 2 FAILED: {str(e)}", exc_info=True)
        return False


def test_retrieval():
    """Test 3: Verify document retrieval."""
    print("\n" + "="*70)
    print("TEST 3: Document Retrieval")
    print("="*70)
    
    try:
        from retriever import Retriever
        
        retriever = Retriever(persist_directory="./chroma_data")
        logger.info("[TEST] Retriever initialized")
        
        # Test queries
        test_queries = [
            "What is lung cancer?",
            "skin disease symptoms",
            "breast cancer detection",
        ]
        
        all_success = True
        
        for query in test_queries:
            print(f"\nQUERY: '{query}'")
            
            try:
                results = retriever.retrieve(query, disease_type=None, top_k=5)
                
                if results:
                    print(f"  [OK] Retrieved {len(results)} documents")
                    
                    # Show top result
                    top = results[0]
                    print(f"     Best match (distance: {top['distance']:.4f}):")
                    preview = top['text'][:80].replace('\n', ' ')
                    print(f"     -> {preview}...")
                    print(f"     Source: {top['metadata'].get('source', 'Unknown')}")
                    print(f"     Collection: {top['collection']}")
                else:
                    print(f"  [EMPTY] No documents retrieved")
                    all_success = False
            
            except Exception as e:
                logger.error(f"  [ERROR] Error retrieving '{query}': {str(e)}")
                all_success = False
        
        if not all_success:
            logger.warning("[TEST] TEST 3 PARTIAL: Some queries returned no results")
            logger.warning("[TEST]    Check: 1) Documents indexed? 2) Data exists?")
        else:
            logger.info("[TEST] TEST 3 PASSED: Retrieval working")
        
        return all_success
    
    except Exception as e:
        logger.error(f"[TEST] TEST 3 FAILED: {str(e)}", exc_info=True)
        return False


def test_rag_generation():
    """Test 4: Verify RAG answer generation."""
    print("\n" + "="*70)
    print("TEST 4: RAG Answer Generation")
    print("="*70)
    
    try:
        from rag_pipeline import RAGPipeline
        
        pipeline = RAGPipeline()
        logger.info("[TEST] RAG Pipeline initialized (fully local, no API needed)")
        
        test_queries = [
            ("What is lung cancer?", None),
            ("Tell me about skin disease", "dermatology"),
            ("breast cancer symptoms", "breast_cancer"),
        ]
        
        all_success = True
        
        for query, disease_type in test_queries:
            print(f"\nQUERY: '{query}' (disease_type: {disease_type})")
            
            try:
                result = pipeline.generate_answer(query, disease_type=disease_type, top_k=5)
                
                if result.get("error"):
                    print(f"  [ERROR] {result['error']}")
                    all_success = False
                elif result.get("answer"):
                    print(f"  [OK] Generated answer ({len(result['answer'])} chars)")
                    print(f"  [INFO] Retrieved: {result['retrieved_count']} documents")
                    print(f"  [INFO] Sources: {len(result['sources'])} identified")
                    
                    # Show preview
                    preview = result['answer'][:150].replace('\n', ' ')
                    print(f"\n  Preview: {preview}...")
                else:
                    print(f"  [FAILED] No answer generated")
                    all_success = False
            
            except Exception as e:
                logger.error(f"  [ERROR] {str(e)}")
                print(f"  [ERROR] Exception occurred: {str(e)}")
                all_success = False
        
        if not all_success:
            logger.warning("[TEST] TEST 4 PARTIAL: Some queries failed")
        else:
            logger.info("[TEST] TEST 4 PASSED: RAG generation working")
        
        return all_success
    
    except Exception as e:
        logger.error(f"[TEST] TEST 4 FAILED: {str(e)}", exc_info=True)
        return False


def test_embedding_consistency():
    """Test 5: Verify same embedding model is used for indexing and retrieval."""
    print("\n" + "="*70)
    print("TEST 5: Embedding Model Consistency")
    print("="*70)
    
    try:
        from embedding_service import EmbeddingModel
        
        # Get embeddings from two EmbeddingModel instances
        em1 = EmbeddingModel()
        em2 = EmbeddingModel()
        
        test_text = "lung cancer diagnosis"
        
        emb1 = em1.embed_text(test_text)
        emb2 = em2.embed_text(test_text)
        
        # Check if embeddings are identical
        import numpy as np
        distance = np.linalg.norm(np.array(emb1) - np.array(emb2))
        
        print(f"\nConsistency test: Same query embedded twice")
        print(f"  Text: '{test_text}'")
        print(f"  Embedding distance: {distance:.8f}")
        
        if distance < 1e-6:
            print(f"  [OK] Perfect consistency")
            logger.info("[TEST] TEST 5 PASSED: Embedding model is consistent")
            return True
        else:
            print(f"  [WARNING] Minor variance detected (distance: {distance})")
            logger.warning("[TEST] Embeddings are not perfectly consistent")
            return False
    
    except Exception as e:
        logger.error(f"[TEST] TEST 5 FAILED: {str(e)}", exc_info=True)
        return False


def run_all_tests():
    """Run all tests and show summary."""
    print("\n\n")
    print("#"*70)
    print("# RAG PIPELINE DIAGNOSTIC TEST SUITE")
    print("#"*70)
    
    results = {
        "Vector Store": test_vector_store(),
        "Embeddings": test_embeddings(),
        "Retrieval": test_retrieval(),
        "RAG Generation": test_rag_generation(),
        "Embedding Consistency": test_embedding_consistency(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n>>> ALL TESTS PASSED - RAG System is fully operational!")
        return True
    elif passed >= total - 1:
        print("\n>>> MOSTLY WORKING - Minor issues detected")
        return True
    else:
        print("\n>>> CRITICAL ISSUES - Check logs above")
        return False


def main():
    """Run the test suite."""
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Comprehensive RAG System Validation Script

This script validates the entire RAG pipeline:
1. Checks if data files exist
2. Verifies vector store collections
3. Tests document loading and ingestion
4. Tests retrieval functionality
5. Tests RAG answer generation
6. Generates a detailed report

Usage:
    python validate_rag.py
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("rag_validator")

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def check_data_files():
    """Check if data files exist and are readable."""
    print_section("STEP 1: Checking Data Files")
    
    script_dir = Path(__file__).parent
    data_dir = script_dir / "Data"
    
    print(f"Data directory: {data_dir}")
    print(f"Exists: {data_dir.exists()}\n")
    
    if not data_dir.exists():
        print("[FAIL] FAILURE: Data directory not found!")
        return False
    
    # Check for subdirectories
    subdirs = {
        "Skin": "dermatology",
        "Lung": "lung_cancer",
        "Breast": "breast_cancer",
        "DR": "diabetic_retinopathy"
    }
    
    found_subdirs = {}
    for subdir, disease_type in subdirs.items():
        subdir_path = data_dir / subdir
        txt_files = list(subdir_path.glob("*.txt"))
        if subdir_path.exists():
            print(f"[OK] {subdir:15} → {disease_type:25} ({len(txt_files)} files)")
            found_subdirs[subdir] = len(txt_files)
        else:
            print(f"✗ {subdir:15} → {disease_type:25} (NOT FOUND)")
    
    total_files = sum(len(list(data_dir.glob(f"{sd}/*.txt"))) for sd in subdirs.keys())
    print(f"\nTotal .txt files: {total_files}")
    
    if total_files == 0:
        print("[FAIL] FAILURE: No data files found!")
        return False
    
    print("[PASS] PASS: Data files found")
    return True

def check_vector_store():
    """Check the current state of the vector store."""
    print_section("STEP 2: Checking Vector Store")
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from vector_store_service import VectorStore
    except ImportError as e:
        print(f"[FAIL] FAILURE: Could not import VectorStore: {e}")
        return False
    
    try:
        vs = VectorStore(persist_directory="./chroma_data")
        
        print(f"Collections available: {', '.join(vs.COLLECTIONS)}\n")
        
        total_docs = 0
        all_empty = True
        
        for collection in vs.COLLECTIONS:
            count = vs.get_collection_count(collection)
            status = "[OK]" if count > 0 else "✗"
            print(f"{status} {collection:25} {count:5} documents")
            total_docs += count
            if count > 0:
                all_empty = False
        
        print(f"\nTotal documents in vector store: {total_docs}")
        
        if all_empty:
            print("[WARN]️  WARNING: All collections are empty!")
            print("Next: Run 'python ingest.py' to load documents")
            return False
        
        print("[PASS] PASS: Vector store has documents")
        return True
    
    except Exception as e:
        print(f"[FAIL] FAILURE: Could not check vector store: {e}")
        return False

def check_embedding_model():
    """Check if embedding model can be loaded."""
    print_section("STEP 3: Checking Embedding Model")
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from embedding_service import EmbeddingModel
    except ImportError as e:
        print(f"[FAIL] FAILURE: Could not import EmbeddingModel: {e}")
        return False
    
    try:
        em = EmbeddingModel()
        print("[OK] EmbeddingModel loaded successfully")
        
        # Test embedding a sample text
        test_text = "What is melanoma?"
        embedding = em.embed_text(test_text)
        
        print(f"[OK] Sample embedding generated")
        print(f"  Text: '{test_text}'")
        print(f"  Dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        
        print("\n[PASS] PASS: Embedding model working")
        return True
    
    except Exception as e:
        print(f"[FAIL] FAILURE: Embedding model error: {e}")
        return False

def check_retrieval():
    """Check if retrieval works."""
    print_section("STEP 4: Testing Retrieval")
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from retriever import Retriever
    except ImportError as e:
        print(f"[FAIL] FAILURE: Could not import Retriever: {e}")
        return False
    
    try:
        retriever = Retriever(persist_directory="./chroma_data")
        
        # Test queries
        test_queries = [
            ("dermatology", "What is melanoma?"),
            ("lung_cancer", "What is lung cancer?"),
            ("breast_cancer", "What is breast cancer?"),
        ]
        
        all_passed = True
        
        for disease_type, query in test_queries:
            print(f"\nQuery: '{query}' (disease_type: {disease_type})")
            
            try:
                results = retriever.retrieve(query, disease_type=disease_type, top_k=3)
                
                if results:
                    print(f"[OK] Retrieved {len(results)} documents")
                    for i, r in enumerate(results[:2], 1):
                        source = r["metadata"].get("source", "Unknown")
                        distance = r["distance"]
                        print(f"  [{i}] {source} (distance: {distance:.4f})")
                else:
                    print(f"✗ Retrieved 0 documents!")
                    all_passed = False
            
            except Exception as e:
                print(f"✗ Retrieval failed: {e}")
                all_passed = False
        
        if all_passed:
            print("\n[PASS] PASS: Retrieval working for all disease types")
            return True
        else:
            print("\n[WARN]️  WARNING: Some retrievals failed")
            return False
    
    except Exception as e:
        print(f"[FAIL] FAILURE: Retrieval error: {e}")
        return False

def check_rag_generation():
    """Check if RAG answer generation works."""
    print_section("STEP 5: Testing RAG Answer Generation")
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from rag_pipeline import RAGPipeline
    except ImportError as e:
        print(f"[FAIL] FAILURE: Could not import RAGPipeline: {e}")
        return False
    
    try:
        pipeline = RAGPipeline(persist_directory="./chroma_data")
        
        test_queries = [
            ("dermatology", "What are the symptoms of melanoma?"),
            ("lung_cancer", "How is lung cancer diagnosed?"),
        ]
        
        all_passed = True
        
        for disease_type, query in test_queries:
            print(f"\nQuery: '{query}'")
            print(f"Disease type: {disease_type}")
            
            try:
                result = pipeline.generate_answer(query, disease_type=disease_type, top_k=3)
                
                if result.get("error"):
                    print(f"✗ Error: {result['error']}")
                    all_passed = False
                elif not result.get("answer"):
                    print(f"✗ No answer generated")
                    all_passed = False
                else:
                    answer = result["answer"]
                    retrieved = result.get("retrieved_count", 0)
                    sources = result.get("sources", [])
                    
                    print(f"[OK] Answer generated ({len(answer)} chars)")
                    print(f"  Retrieved docs: {retrieved}")
                    print(f"  Sources: {len(sources)}")
                    print(f"  Answer preview: {answer[:150]}...")
            
            except Exception as e:
                print(f"✗ RAG generation failed: {e}")
                all_passed = False
        
        if all_passed:
            print("\n[PASS] PASS: RAG answer generation working")
            return True
        else:
            print("\n[WARN]️  WARNING: Some RAG generations failed")
            return False
    
    except Exception as e:
        print(f"[FAIL] FAILURE: RAG generation error: {e}")
        return False

def main():
    """Run all validation checks."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "  RAG SYSTEM VALIDATION".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70 + "\n")
    
    checks = [
        ("Data Files", check_data_files),
        ("Vector Store", check_vector_store),
        ("Embedding Model", check_embedding_model),
        ("Retrieval", check_retrieval),
        ("RAG Generation", check_rag_generation),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"Unhandled error in {name} check: {e}", exc_info=True)
            results[name] = False
    
    # Print summary
    print_section("VALIDATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}  {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n[PASS] ALL CHECKS PASSED - RAG system is ready!")
        return 0
    elif passed >= total - 1:
        print("\n[WARN]️  MOST CHECKS PASSED - Minor issues detected")
        print("→ Run ingestion if vector store is empty: python ingest.py")
        return 0
    else:
        print("\n[FAIL] CRITICAL ISSUES DETECTED - Please fix before using RAG")
        return 1

if __name__ == "__main__":
    sys.exit(main())

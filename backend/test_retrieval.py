import sys
sys.path.insert(0, 'app/rag')
from retriever import Retriever

retriever = Retriever(persist_directory='./app/rag/chroma_data')

# Test retrieval with disease type
print("=" * 70)
print("Testing retrieval for dermatology query")
print("=" * 70)
results = retriever.retrieve('What is melanoma?', disease_type='dermatology', top_k=5)
print(f'Retrieved {len(results)} documents')
for i, r in enumerate(results, 1):
    print(f'  [{i}] {r["metadata"].get("source", "Unknown")} (distance: {r["distance"]:.4f})')

# Test retrieval without disease type
print("\n" + "=" * 70)
print("Testing retrieval for general query (no disease type)")
print("=" * 70)
results2 = retriever.retrieve('What is lung cancer?', disease_type=None, top_k=5)
print(f'Retrieved {len(results2)} documents')
for i, r in enumerate(results2, 1):
    print(f'  [{i}] {r["metadata"].get("source", "Unknown")} | Collection: {r["collection"]} (distance: {r["distance"]:.4f})')

# Test RAG pipeline
print("\n" + "=" * 70)
print("Testing RAG pipeline")
print("=" * 70)
sys.path.insert(0, 'app/rag')
from rag_pipeline import RAGPipeline

pipeline = RAGPipeline(persist_directory='./app/rag/chroma_data')
result = pipeline.generate_answer('What is melanoma and how is it treated?', disease_type='dermatology', top_k=5)

print(f'Answer: {result["answer"][:200]}...')
print(f'Retrieved {result["retrieved_count"]} documents')
print(f'Sources: {len(result["sources"])} sources')

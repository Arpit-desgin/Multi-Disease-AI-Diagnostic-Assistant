"""
Chatbot Service Integration Test

This script simulates the chatbot endpoint behavior to ensure
medical_chat() returns proper answers from the RAG system.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".." / "services"))
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("  CHATBOT SERVICE INTEGRATION TEST")
print("="*70 + "\n")

# Test the medical_chat function
print("[TEST] Simulating chatbot request...")
print("-" * 70)

try:
    from chatbot_service import _rag_chat
    
    # Simulate a user message
    user_message = "What are the symptoms of melanoma?"
    prompt = f"User question: {user_message}\nRespond with medical information."
    
    print(f"User Message: '{user_message}'")
    print(f"Disease Type (auto-detected): dermatology")
    print()
    
    # Call the RAG chat function
    answer, is_fallback = _rag_chat(prompt, user_message, diagnosis_context=None)
    
    print(f"Response Type: {'FALLBACK' if is_fallback else 'RAG-BASED'}")
    print(f"Response Length: {len(answer)} characters")
    print(f"Uses Retrieved Documents: {not is_fallback}")
    print()
    
    if not is_fallback:
        print("[OK] SUCCESS: Chatbot returned RAG-based answer from documents")
        print()
        print("Answer Preview (first 200 chars):")
        print(f"  {answer[:200]}...")
    else:
        print("[FAIL] FAILURE: Chatbot using fallback response (no RAG)")
        print()
        print("Answer:")
        print(f"  {answer}")
    
    print()
    print("-" * 70)
    
    if not is_fallback and len(answer) > 100:
        print("[OK] PASS - Chatbot integration test SUCCESSFUL")
        print("       Medical answers are being retrieved from the RAG system")
    else:
        print("[FAIL] FAIL - Chatbot test FAILED")
        print("       Not using RAG system or no documents retrieved")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70 + "\n")

sys.exit(0)

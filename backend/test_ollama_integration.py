#!/usr/bin/env python
"""
Quick Test: Ollama Integration

Tests that Ollama is properly configured and can generate answers.
Run this AFTER setting up Ollama.

Usage:
    python test_ollama_integration.py
"""

import sys
import logging
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent / "app" / "services"))
sys.path.insert(0, str(Path(__file__).parent / "app" / "rag"))

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def test_ollama_service():
    """Test basic Ollama service functionality."""
    
    print("\n" + "="*70)
    print("OLLAMA INTEGRATION TEST")
    print("="*70 + "\n")
    
    # Test 1: Import
    print("[TEST 1] Importing ollama_service...")
    try:
        from ollama_service import (
            verify_setup,
            generate_answer,
            get_available_models,
            OLLAMA_AVAILABLE
        )
        print("✅ PASS: Import successful")
    except Exception as e:
        print(f"❌ FAIL: Import error: {e}")
        return False
    
    # Test 2: Check library installed
    print("\n[TEST 2] Checking if ollama library is installed...")
    if not OLLAMA_AVAILABLE:
        print("❌ FAIL: ollama library not installed")
        print("→ Fix: pip install ollama")
        return False
    print("✅ PASS: ollama library is available")
    
    # Test 3: Verify setup
    print("\n[TEST 3] Verifying Ollama setup...")
    try:
        setup = verify_setup()
        print(f"  Library: {setup['ollama_library_installed']}")
        print(f"  Server: {setup['ollama_server_running']}")
        print(f"  Models: {setup['available_models']}")
        
        if not setup['ollama_server_running']:
            print("\n⚠️  WARNING: Ollama server is NOT running")
            print("→ Start it with: ollama serve")
            print("→ Then run this test again")
            return False
        
        if not setup['default_model_available']:
            print("\n⚠️  WARNING: Mistral model not available")
            print("→ Pull it with: ollama pull mistral")
            return False
        
        print("✅ PASS: Ollama is properly configured")
    except Exception as e:
        print(f"❌ FAIL: Setup verification error: {e}")
        return False
    
    # Test 4: Test generation
    print("\n[TEST 4] Testing answer generation...")
    try:
        test_context = """
        Lung cancer is the most common cause of cancer deaths worldwide.
        Risk factors include smoking, air pollution, and genetic factors.
        Symptoms may include persistent cough, chest pain, and shortness of breath.
        Treatment options include surgery, radiation, and chemotherapy.
        Early detection significantly improves survival rates.
        """
        
        test_question = "What is lung cancer?"
        
        print(f"  Context: {len(test_context)} characters")
        print(f"  Question: {test_question}")
        print("  Calling Ollama...\n")
        
        result = generate_answer(
            question=test_question,
            context=test_context,
            model="mistral",
            temperature=0.3
        )
        
        if result.get("fallback"):
            print(f"❌ FAIL: Generation failed (fallback mode)")
            print(f"  Error: {result.get('error')}")
            return False
        
        answer = result.get("answer", "")
        if not answer:
            print("❌ FAIL: Empty answer")
            return False
        
        print(f"✅ PASS: Generation successful")
        print(f"\n  Generated Answer ({len(answer)} chars):")
        print("  " + "-"*66)
        for line in answer.split('\n')[:5]:  # Show first 5 lines
            print(f"  {line}")
        if len(answer.split('\n')) > 5:
            print("  ...")
        print("  " + "-"*66)
        
    except Exception as e:
        print(f"❌ FAIL: Generation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nNext steps:")
    print("1. Start backend: uvicorn app.main:app --reload")
    print("2. Test chatbot: curl -X POST http://localhost:8000/api/chatbot/chat \\")
    print("                   -H 'Content-Type: application/json' \\")
    print("                   -d '{\"session_id\": \"test\", \"message\": \"What is lung cancer?\"}'")
    print("\n")
    
    return True


if __name__ == "__main__":
    success = test_ollama_service()
    sys.exit(0 if success else 1)

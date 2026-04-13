#!/usr/bin/env python
"""
Ollama Setup Verification Script

Checks if Ollama is properly installed and configured.
Provides diagnostic information and setup instructions.

Usage:
    python verify_ollama_setup.py
"""

import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def verify_ollama_setup():
    """Verify Ollama installation and configuration."""
    
    print("\n" + "="*70)
    print("OLLAMA SETUP VERIFICATION")
    print("="*70 + "\n")
    
    # Step 1: Check if ollama Python library is installed
    print("[1] Checking if ollama Python library is installed...")
    try:
        import ollama
        print("    ✅ ollama library is installed")
    except ImportError:
        print("    ❌ ollama library NOT installed")
        print("    → Fix: pip install ollama")
        return False
    
    # Step 2: Import our service
    print("\n[2] Checking if ollama_service.py is available...")
    try:
        sys.path.insert(0, "app/services")
        from ollama_service import verify_setup, OLLAMA_AVAILABLE
        print("    ✅ ollama_service.py found and imported")
    except ImportError as e:
        print(f"    ❌ Failed to import ollama_service: {e}")
        return False
    
    # Step 3: Verify Ollama service setup
    print("\n[3] Verifying Ollama service configuration...")
    try:
        from ollama_service import verify_setup
        setup_status = verify_setup()
        
        print(f"\n    Library installed: {setup_status['ollama_library_installed']}")
        print(f"    Server running: {setup_status['ollama_server_running']}")
        print(f"    Available models: {setup_status['available_models']}")
        print(f"    Mistral available: {setup_status['default_model_available']}")
        
        if setup_status['errors']:
            print(f"\n    Errors:")
            for error in setup_status['errors']:
                print(f"      → {error}")
            return False
        
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        return False
    
    # Step 4: Test connectivity
    print("\n[4] Testing Ollama server connectivity...")
    try:
        from ollama_service import _is_ollama_running
        if _is_ollama_running():
            print("    ✅ Ollama server is running and responsive")
        else:
            print("    ❌ Ollama server not responding")
            print("    → Run: ollama serve")
            return False
    except Exception as e:
        print(f"    ❌ Connectivity test failed: {e}")
        return False
    
    # Step 5: Test model availability
    print("\n[5] Checking if Mistral model is available...")
    try:
        from ollama_service import get_available_models
        models = get_available_models()
        if "mistral" in models:
            print("    ✅ Mistral model is available")
        else:
            print("    ⚠️  Mistral model not found")
            print(f"    Available models: {models}")
            print("    → To pull mistral: ollama pull mistral")
            return False
    except Exception as e:
        print(f"    Error checking models: {e}")
        return False
    
    # Step 6: Test generation
    print("\n[6] Testing answer generation...")
    try:
        from ollama_service import generate_answer
        
        test_context = "Lung cancer is a malignant tumor of the lungs."
        test_question = "What is lung cancer?"
        
        result = generate_answer(
            question=test_question,
            context=test_context,
            model="mistral"
        )
        
        if result.get("answer") and not result.get("fallback"):
            print("    ✅ Generation test successful")
            print(f"    Generated: {result['answer'][:100]}...")
        else:
            print(f"    ❌ Generation failed: {result.get('error')}")
            return False
    
    except Exception as e:
        print(f"    ❌ Generation test failed: {e}")
        return False
    
    print("\n" + "="*70)
    print("✅ ALL CHECKS PASSED - Ollama is ready to use!")
    print("="*70 + "\n")
    return True


def print_setup_instructions():
    """Print detailed setup instructions."""
    
    print("\n" + "="*70)
    print("OLLAMA SETUP INSTRUCTIONS")
    print("="*70 + "\n")
    
    print("Step 1: Install Ollama")
    print("  • Download from: https://ollama.ai")
    print("  • Follow platform-specific installation instructions")
    print("  • Verify: ollama --version\n")
    
    print("Step 2: Start Ollama Server")
    print("  • Open a new terminal")
    print("  • Run: ollama serve")
    print("  • Keep this terminal open (don't close it)\n")
    
    print("Step 3: Pull Mistral Model")
    print("  • Open another terminal")
    print("  • Run: ollama pull mistral")
    print("  • Wait for download to complete (first time ~2GB)\n")
    
    print("Step 4: Install Python Package")
    print("  • In backend directory, run:")
    print("    pip install ollama\n")
    
    print("Step 5: Verify Setup")
    print("  • Run: python verify_ollama_setup.py")
    print("  • All checks should pass\n")
    
    print("Step 6: Start Backend")
    print("  • Make sure 'ollama serve' is still running in another terminal")
    print("  • Run: uvicorn app.main:app --reload\n")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    # Print instructions
    print_setup_instructions()
    
    # Verify setup
    success = verify_ollama_setup()
    
    if not success:
        print("\n⚠️  Setup verification failed. Please follow the setup instructions above.")
        sys.exit(1)
    else:
        print("✨ You're all set! The backend will use Ollama for LLM-powered answers.")
        sys.exit(0)

"""
Ollama LLM Integration Service

Provides local LLM-based answer generation using Ollama.
Supports both generation and chat-based endpoints.

Features:
- Local model execution (no external API calls)
- Structured prompt templates for medical contexts
- Error handling with graceful degradation
- Streaming and non-streaming modes
"""

import logging
from typing import Optional, Dict, Any, List
import sys
import os
from pathlib import Path

logger = logging.getLogger("app.ollama_service")

# Try to import ollama library
try:
    import ollama
    OLLAMA_AVAILABLE = True
    logger.info("[OLLAMA] ollama library imported successfully")
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("[OLLAMA] ollama library not installed - LLM generation will be disabled")


# Adaptive medical prompt templates based on question type
def _get_medical_prompt(question: str, context: str) -> str:
    """
    Get an adaptive medical prompt based on the question type.
    
    Args:
        question: User's medical question
        context: Retrieved medical documents
        
    Returns:
        Tailored prompt for the specific question type
    """
    question_lower = question.lower()
    
    # Detect question type
    if any(word in question_lower for word in ["what is", "define", "definition", "what's"]):
        return f"""You are a medical information assistant. Based on the provided medical documents, answer the user's question concisely and accurately.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide ONLY a brief definition/overview (2-3 sentences maximum)
2. Be medically accurate but use plain language
3. Do not include symptoms, causes, or treatment unless asked
4. If information is not available, say so clearly

RESPONSE:"""
    
    elif any(word in question_lower for word in ["symptom", "sign", "manifestation", "present"]):
        return f"""You are a medical information assistant. Based on the provided medical documents, answer the user's question concisely and accurately.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide ONLY the symptoms or signs (bullet points, 3-5 max)
2. Be medically accurate but use plain language
3. Do not include definition, causes, or treatment unless asked
4. Keep it brief and focused

RESPONSE:"""
    
    elif any(word in question_lower for word in ["cause", "cause", "reason", "etiology", "risk factor"]):
        return f"""You are a medical information assistant. Based on the provided medical documents, answer the user's question concisely and accurately.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide ONLY the causes or risk factors (bullet points, 3-5 max)
2. Be medically accurate but use plain language
3. Do not include definition, symptoms, or treatment unless asked
4. Keep it brief and focused

RESPONSE:"""
    
    elif any(word in question_lower for word in ["treatment", "manage", "therapy", "cure", "treat", "manage"]):
        return f"""You are a medical information assistant. Based on the provided medical documents, answer the user's question concisely and accurately.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide ONLY the treatment or management options (bullet points, 3-5 max)
2. Be medically accurate but use plain language
3. Do not include definition, symptoms, or causes unless asked
4. Keep it brief and focused

RESPONSE:"""
    
    else:
        # Default: generic comprehensive answer
        return f"""You are a medical information assistant. Based on the provided medical documents, answer the user's question clearly and accurately.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Provide a clear, concise answer based on the retrieved documents
2. Keep response brief and focused
3. Use plain language
4. If information is not available, say so clearly

RESPONSE:"""


def _clean_text(text: str) -> str:
    """
    Clean medical text by removing tags, duplicates, and formatting artifacts.
    
    Removes tags like [DEF], [SYM], [CAUSE], [RX] and normalizes whitespace.
    Removes duplicate paragraphs/chunks.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    import re
    
    # Remove medical document tags
    text = re.sub(r'\[DEF\]|\[SYM\]|\[CAUSE\]|\[RX\]|\[NOTE\]|\[TREATMENT\]|\[DIAGNOSIS\]', '', text)
    
    # Remove markdown-style tags if present
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **text** → text
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *text* → text
    text = re.sub(r'_(.*?)_', r'\1', text)        # _text_ → text
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Clean up line breaks
    text = text.strip()
    
    # Remove duplicate chunks (simple approach: split by periods and deduplicate)
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    unique_sentences = []
    seen = set()
    
    for sentence in sentences:
        # Normalize for comparison
        normalized = sentence.lower().strip()
        if normalized not in seen and len(normalized) > 10:  # Skip very short duplicates
            unique_sentences.append(sentence)
            seen.add(normalized)
    
    # Rejoin
    text = '. '.join(unique_sentences)
    if text and not text.endswith('.'):
        text += '.'
    
    return text


def _is_ollama_running() -> bool:
    """
    Check if Ollama server is running.
    
    Returns:
        True if Ollama is running, False otherwise
    """
    if not OLLAMA_AVAILABLE:
        return False
    
    try:
        # Try to list models - fastest health check
        ollama.list()
        logger.info("[OLLAMA] ✅ Server is running")
        return True
    except Exception as e:
        logger.warning(f"[OLLAMA] ⚠️  Server not responding: {str(e)}")
        return False


def get_available_models() -> List[str]:
    """
    Get list of available models from Ollama.
    
    Returns:
        List of model names
    """
    if not OLLAMA_AVAILABLE:
        logger.warning("[OLLAMA] ollama library not available")
        return []
    
    if not _is_ollama_running():
        logger.warning("[OLLAMA] Ollama server not running")
        return []
    
    try:
        models = ollama.list()
        model_names = [m.get('name', '').split(':')[0] for m in models.get('models', [])]
        logger.info(f"[OLLAMA] Available models: {model_names}")
        return model_names
    except Exception as e:
        logger.error(f"[OLLAMA] Failed to list models: {str(e)}")
        return []


def generate_answer(
    question: str,
    context: str,
    model: str = "mistral",
    temperature: float = 0.3,
    top_p: float = 0.9
) -> Dict[str, Any]:
    """
    Generate a medical answer using Ollama chat API.
    
    Uses adaptive prompts based on question type for targeted responses.
    
    Args:
        question: User's medical question
        context: Retrieved medical documents (concatenated text)
        model: Model name (default: "mistral")
        temperature: Sampling temperature (0.0-1.0)
        top_p: Nucleus sampling parameter
        
    Returns:
        Dictionary with:
        - answer: Generated response
        - model: Model used
        - error: Error message if any
        - fallback: True if using fallback
    """
    if not OLLAMA_AVAILABLE:
        logger.error("[OLLAMA] ❌ ollama library not installed")
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": "Ollama library not installed",
            "fallback": True
        }
    
    if not _is_ollama_running():
        logger.error("[OLLAMA] ❌ Ollama server not running")
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": "Ollama server not running",
            "fallback": True
        }
    
    try:
        # Clean context
        context = _clean_text(context)
        
        # Get adaptive prompt based on question type
        prompt = _get_medical_prompt(question, context)
        
        logger.info(f"[OLLAMA] 📋 Calling {model} for answer generation")
        logger.info(f"[OLLAMA] ❓ Question: {question[:80]}")
        logger.info(f"[OLLAMA] 📄 Context length: {len(context)} chars, Prompt length: {len(prompt)} chars")
        
        # Call Ollama using CHAT API for better structured responses
        # Note: Ollama Python client does NOT support temperature/top_p in chat() - use prompt only
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        generated_text = response.get("message", {}).get("content", "").strip()
        
        logger.info(f"[OLLAMA] ✅ Response generated ({len(generated_text)} chars)")
        
        return {
            "answer": generated_text,
            "model": model,
            "error": None,
            "fallback": False
        }
    
    except Exception as e:
        logger.error(f"[OLLAMA] ❌ Generation failed: {str(e)}", exc_info=True)
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": f"Generation failed: {str(e)}",
            "fallback": True
        }


def chat(
    messages: List[Dict[str, str]],
    model: str = "mistral",
    temperature: float = 0.3,
    top_p: float = 0.9
) -> Dict[str, Any]:
    """
    Chat with Ollama model.
    
    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts
        model: Model name (default: "mistral")
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        
    Returns:
        Dictionary with:
        - answer: Generated response
        - model: Model used
        - error: Error message if any
    """
    if not OLLAMA_AVAILABLE:
        logger.error("[OLLAMA] ollama library not installed")
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": "Ollama library not installed"
        }
    
    if not _is_ollama_running():
        logger.error("[OLLAMA] Ollama server not running")
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": "Ollama server not running"
        }
    
    try:
        logger.info(f"[OLLAMA] 💬 Chat call with {model}")
        logger.info(f"[OLLAMA] 📨 Number of messages: {len(messages)}")
        
        # Call Ollama using correct API (Ollama Python client does NOT support temperature/top_p)
        response = ollama.chat(
            model=model,
            messages=messages
        )
        
        answer = response.get('message', {}).get('content', '').strip()
        
        logger.info(f"[OLLAMA] ✅ Chat response generated ({len(answer)} chars)")
        
        return {
            "answer": answer,
            "model": model,
            "error": None
        }
    
    except Exception as e:
        logger.error(f"[OLLAMA] ❌ Chat failed: {str(e)}", exc_info=True)
        return {
            "answer": _get_fallback_response(),
            "model": model,
            "error": f"Chat failed: {str(e)}"
        }


def _get_fallback_response() -> str:
    """
    Get fallback response when Ollama is unavailable.
    
    Returns:
        Helpful error message with setup instructions
    """
    return (
        "I'm unable to generate a detailed response right now because the local LLM service "
        "(Ollama) is not running. To enable this feature:\n\n"
        "1. Install Ollama from https://ollama.ai\n"
        "2. Run: ollama serve\n"
        "3. In another terminal: ollama pull mistral\n"
        "4. Then try again\n\n"
        "For now, I can still retrieve relevant medical information from documents. "
        "Please try asking your question again with more specific terms."
    )


def verify_setup() -> Dict[str, Any]:
    """
    Verify Ollama setup and return diagnostic information.
    
    Returns:
        Dictionary with setup status and diagnostic info
    """
    result = {
        "ollama_library_installed": OLLAMA_AVAILABLE,
        "ollama_server_running": False,
        "available_models": [],
        "default_model_available": False,
        "errors": []
    }
    
    if not OLLAMA_AVAILABLE:
        result["errors"].append("ollama library not installed - run: pip install ollama")
        return result
    
    if _is_ollama_running():
        result["ollama_server_running"] = True
        result["available_models"] = get_available_models()
        result["default_model_available"] = "mistral" in result["available_models"]
    else:
        result["errors"].append("Ollama server not running")
        result["errors"].append("To start: ollama serve from terminal")
    
    return result

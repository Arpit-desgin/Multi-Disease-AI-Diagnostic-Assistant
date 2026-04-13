from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
import asyncio
import sys
from pathlib import Path

logger = logging.getLogger("app.chatbot_service")

# Simple in-memory session store; swap to Redis in production.
_sessions: Dict[str, List[Dict[str, str]]] = {}
_MAX_HISTORY = 10

# In-memory request deduplication: prevents concurrent duplicate calls for same session
_session_locks: Dict[str, asyncio.Lock] = {}

# Global RAG pipeline instance (loaded once, reused for all requests)
_rag_pipeline = None


def _get_rag_pipeline():
    """
    Lazy load local RAG pipeline once on first use.
    This ensures the vector index is loaded only once, not per request.
    
    Uses fully local embeddings (SentenceTransformer) - NO API keys required.
    """
    global _rag_pipeline
    
    if _rag_pipeline is None:
        try:
            # Add rag module to path
            rag_module_path = Path(__file__).parent.parent / "rag"
            if str(rag_module_path) not in sys.path:
                sys.path.insert(0, str(rag_module_path))
            
            from rag_pipeline import RAGPipeline
            
            # Initialize local RAG pipeline (no API key needed)
            _rag_pipeline = RAGPipeline()
            logger.info("[RAG] ✅ RAG pipeline loaded successfully")
            logger.info("[RAG] Using local embeddings (sentence-transformers: all-MiniLM-L6-v2)")
            logger.info("[RAG] Fully offline operation - no external API calls")
        except Exception as e:
            logger.error(f"[RAG] Failed to load RAG pipeline: {str(e)}", exc_info=True)
            _rag_pipeline = None
    
    return _rag_pipeline


def _get_history(session_id: str) -> List[Dict[str, str]]:
    return _sessions.setdefault(session_id, [])


def _append_message(session_id: str, role: str, content: str) -> None:
    history = _get_history(session_id)
    history.append({"role": role, "content": content})
    # keep only last N messages
    if len(history) > _MAX_HISTORY:
        del history[0 : len(history) - _MAX_HISTORY]


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def _rag_chat(prompt: str, user_message: str, diagnosis_context: Dict[str, Any] | None = None) -> tuple[str, bool]:
    """
    Call local RAG pipeline for medical question answering.
    
    Uses fully local, offline processing with SentenceTransformer embeddings.
    No API keys required - runs completely locally.
    
    Returns:
        tuple: (response_text, is_fallback)
            - response_text: Generated response from RAG or fallback message
            - is_fallback: True if using fallback due to error
    """
    try:
        pipeline = _get_rag_pipeline()
        
        if pipeline is None:
            logger.error("[RAG] RAG pipeline not initialized")
            return _get_error_response(), True
        
        # Extract disease type hint from user message (optional)
        disease_type = None
        message_lower = user_message.lower()
        if any(term in message_lower for term in ["skin", "dermatology", "mark", "mole", "lesion", "bcc", "melanoma", "eczema"]):
            disease_type = "dermatology"
        elif any(term in message_lower for term in ["lung", "respiratory", "breathing", "cancer"]):
            disease_type = "lung_cancer"
        elif any(term in message_lower for term in ["breast", "mammogram"]):
            disease_type = "breast_cancer"
        elif any(term in message_lower for term in ["dr", "retinopathy", "diabetic", "eye"]):
            disease_type = "diabetic_retinopathy"
        
        # Generate answer using local RAG (no API calls)
        logger.info(f"[RAG] Querying local RAG - question: {user_message[:100]}, disease_type: {disease_type}")
        
        result = pipeline.generate_answer(
            query=user_message,
            disease_type=disease_type,
            top_k=5
        )
        
        if result.get("error"):
            logger.error(f"[RAG] RAG generation error: {result['error']}")
            return _get_error_response(), True
        
        answer = result.get("answer", "")
        model_used = result.get("model", "unknown")
        
        if not answer:
            logger.error("[RAG] Empty answer from RAG pipeline")
            return _get_error_response(), True
        
        logger.info(f"[RAG] ✅ Success - Model: {model_used}, Response length: {len(answer)} chars")
        return answer, False
    
    except Exception as e:
        logger.error(f"[RAG] ❌ Local RAG request failed: {str(e)[:200]}", exc_info=True)
        return _get_error_response(), True



def _get_fallback_response() -> str:
    """Return a helpful fallback response when API quota is exhausted."""
    return (
        "I appreciate your question about your health. Based on your symptoms and the diagnostic results, "
        "here are some key points to consider:\n\n"
        "1. **Understanding your results**: The AI analysis suggests certain patterns, but it's important to remember "
        "this is a screening tool, not a diagnosis.\n"
        "2. **Next steps**: I recommend consulting with a qualified healthcare professional who can review your "
        "complete medical history.\n"
        "3. **Medical guidance**: A doctor can order additional tests if needed and provide personalized treatment recommendations.\n\n"
        "Suggested follow-up actions:\n"
        "- Schedule an appointment with your primary care physician\n"
        "- Bring any test results or symptoms you've noticed\n"
        "- Write down your questions in advance\n"
        "- Consider keeping a symptom diary\n\n"
        "Please consult a qualified doctor for medical decisions."
    )


def _get_error_response() -> str:
    """Return a helpful error response when RAG processing fails."""
    return (
        "I'm having trouble retrieving medical information from the local database right now. "
        "This may be a temporary issue. Please try again in a moment.\n\n"
        "In the meantime, please consult a qualified doctor for medical decisions."
    )


def _build_prompt(
    session_id: str,
    user_message: str,
    diagnosis_context: Dict[str, Any] | None,
) -> str:
    ctx_lines: List[str] = []
    if diagnosis_context:
        ctx_json = json.dumps(diagnosis_context, ensure_ascii=False, indent=2)
        ctx_lines.append("Diagnosis context (from AI and reports):")
        ctx_lines.append(ctx_json)
        ctx_lines.append("")

    history = _get_history(session_id)
    if history:
        ctx_lines.append("Recent conversation:")
        for msg in history:
            prefix = "Patient" if msg["role"] == "user" else "Assistant"
            ctx_lines.append(f"{prefix}: {msg['content']}")
        ctx_lines.append("")

    ctx_lines.append(f"Patient's new message: {user_message}")
    ctx_lines.append(
        "\nRespond concisely. After your main response, provide 2-4 suggested follow-up questions "
        "a patient might ask, as a JSON array named 'suggested_questions'."
    )
    return "\n".join(ctx_lines)


def _parse_suggested_questions(text: str) -> List[str]:
    # Try to find a JSON array in the response.
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("suggested_questions"), list):
            return [str(x) for x in data["suggested_questions"]]
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    # Fallback: naive bullet/line split
    lines = [l.strip("-• ").strip() for l in text.splitlines() if l.strip()]
    # Heuristic: take last few lines
    return lines[-4:] if lines else [
        "What does this mean for my health?",
        "Is this serious or urgent?",
    ]


async def medical_chat(
    session_id: str,
    user_message: str,
    diagnosis_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Process medical chat with RAG pipeline.
    
    Uses asyncio.Lock to prevent concurrent duplicate calls for the same session.
    Ensures only ONE RAG query per user message.
    """
    logger.info(f"[CHAT] Medical chat request - session_id: {session_id}, message_len: {len(user_message)}")
    
    # ✅ DEDUPLICATION: Get or create a lock for this session
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    
    lock = _session_locks[session_id]
    
    # ✅ Acquire lock: Only one chat request per session at a time
    async with lock:
        logger.info(f"[CHAT] Lock acquired for session {session_id}")
        
        _append_message(session_id, "user", user_message)
        prompt = _build_prompt(session_id, user_message, diagnosis_context)

        # Add system prompt
        full_prompt = (
            "You are a compassionate AI medical assistant for a diagnostic platform.\n"
            "You help patients understand their AI diagnosis results, what symptoms mean, and what next steps to take.\n"
            "You always:\n"
            "1. Speak in simple, clear language\n"
            "2. Never replace a doctor's advice\n"
            "3. End every response with: 'Please consult a qualified doctor for medical decisions.'\n"
            "4. If asked about medications or dosages, decline and refer to doctor\n\n" +
            prompt
        )
        
        # ✅ Single RAG query (using vector search + LLM)
        text, is_fallback = _rag_chat(full_prompt, user_message, diagnosis_context)
        
        if is_fallback:
            logger.warning(f"[CHAT] Using fallback response for session {session_id}")
        
        _append_message(session_id, "assistant", text)

        suggested_questions = _parse_suggested_questions(text)
        return {
            "reply": text,
            "session_id": session_id,
            "suggested_questions": suggested_questions,
            "disclaimer": "AI support tool, not medical diagnosis.",
            "is_fallback": is_fallback,  # Flag client to show warning if fallback
        }



from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
import httpx
import asyncio

from app.config import settings


logger = logging.getLogger("app.chatbot_service")

# Simple in-memory session store; swap to Redis in production.
_sessions: Dict[str, List[Dict[str, str]]] = {}
_MAX_HISTORY = 10

# In-memory request deduplication: prevents concurrent duplicate calls for same session
_session_locks: Dict[str, asyncio.Lock] = {}


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


def _gemini_chat_via_rest(prompt: str) -> tuple[str, bool]:
    """
    Call Gemini API via REST - MAX 1 CALL, NO RETRIES.
    
    Returns:
        tuple: (response_text, is_fallback)
            - response_text: Generated response or fallback message
            - is_fallback: True if using fallback due to 429 or error
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required")
    
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            }
        ]
    }
    
    logger.info(f"[GEMINI API] Calling Gemini API - attempt 1 of 1 (NO RETRIES)")
    
    try:
        response = httpx.post(
            f"{api_url}?key={settings.GEMINI_API_KEY}",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        
        # ❌ HANDLE 429 - Return fallback instead of retrying
        if response.status_code == 429:
            logger.warning(f"[GEMINI API] Rate limit hit (429) - returning fallback response (NO RETRY)")
            return _get_fallback_response(), True
        
        response.raise_for_status()
        data = response.json()
        
        # Extract text from response
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        text = part["text"].strip()
                        logger.info(f"[GEMINI API] ✅ Success - response length: {len(text)} chars")
                        return text, False
        
        logger.error(f"[GEMINI API] Unexpected response format: {data}")
        return _get_error_response(), True
        
    except httpx.HTTPStatusError as e:
        # ❌ Explicit 429 handling - NO RETRY
        if e.response.status_code == 429:
            logger.warning(f"[GEMINI API] Rate limit (429) - returning fallback (NO RETRY)")
            return _get_fallback_response(), True
        
        logger.error(f"[GEMINI API] ❌ API error {e.response.status_code}: {e.response.text[:200]}")
        return _get_error_response(), True
        
    except Exception as e:
        logger.error(f"[GEMINI API] ❌ Request failed: {str(e)[:200]}")
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
    """Return a helpful error response when API call fails."""
    return (
        "I'm having trouble connecting to the AI service right now. "
        "This may be temporary. Please try again in a moment.\n\n"
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
    Process medical chat with deduplication and single API call.
    
    Uses asyncio.Lock to prevent concurrent duplicate calls for the same session.
    Ensures only ONE Gemini API call per user message.
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
        
        # ✅ Single API call (no retries, no loops)
        text, is_fallback = _gemini_chat_via_rest(full_prompt)
        
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


from fastapi import APIRouter, Body, Request
import logging

from app.rate_limiter import limiter
from app.services.chatbot_service import clear_session, medical_chat
from app.utils.file_utils import sanitize_string

logger = logging.getLogger("app.chatbot_route")
router = APIRouter(prefix="/chatbot")


@router.post("/message")
@limiter.limit("30/minute")
async def chatbot_message(
    request: Request,
    payload: dict = Body(...),
):
    """
    ✅ Async route to handle chatbot messages.
    - Single API call per request (enforced in service layer with lock)
    - Rate limited to 30/minute per IP
    - No duplicate processing
    """
    logger.info(f"[ROUTE] ✅ RECEIVED CHATBOT REQUEST - Method: {request.method}, Path: {request.url.path}")
    logger.info(f"[ROUTE]    Request headers: Content-Type={request.headers.get('content-type')}, Origin={request.headers.get('origin')}")
    
    session_id = sanitize_string(str(payload.get("session_id") or "")) or ""
    message = sanitize_string(str(payload.get("message") or "")) or ""
    diagnosis_context = payload.get("diagnosis_context") or None

    logger.info(f"[ROUTE]    Payload - session_id: {session_id}, message_length: {len(message)}")

    if not session_id or not message:
        logger.warning(f"[ROUTE]    Missing required fields - session_id: {bool(session_id)}, message: {bool(message)}")
        return {
            "error": "session_id and message are required",
        }

    # ✅ ASYNC CALL: Properly await the async medical_chat function
    response = await medical_chat(session_id=session_id, user_message=message, diagnosis_context=diagnosis_context)
    logger.info(f"[ROUTE]    ✅ Chatbot response sent - reply_length: {len(response.get('reply', ''))}, is_fallback: {response.get('is_fallback', False)}")
    return response


@router.delete("/session/{session_id}")
async def chatbot_clear_session(session_id: str):
    """Clear chat history for a session."""
    clear_session(session_id)
    logger.info(f"[ROUTE] Session cleared: {session_id}")
    return {"session_id": session_id, "cleared": True}


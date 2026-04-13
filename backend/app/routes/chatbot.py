from fastapi import APIRouter, Body, Request
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.rate_limiter import limiter
from app.services.chatbot_service import clear_session, medical_chat
from app.utils.file_utils import sanitize_string

logger = logging.getLogger("app.chatbot_route")
router = APIRouter()


# Request/Response schemas for RAG chatbot
class RAGChatRequest(BaseModel):
    """Schema for RAG-based chat request."""
    question: str
    disease_type: Optional[str] = None


class SourceMetadata(BaseModel):
    """Schema for source document metadata."""
    id: str
    collection: str
    source_file: str
    relevance_score: float
    preview: str


class RAGChatResponse(BaseModel):
    """Schema for RAG-based chat response."""
    answer: str
    sources: List[SourceMetadata]
    retrieved_count: int
    model: str
    error: Optional[str] = None


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


@router.post("/chat", response_model=RAGChatResponse)
@limiter.limit("20/minute")
async def rag_chat(
    request: Request,
    chat_request: RAGChatRequest
):
    """
    Local RAG-based chatbot endpoint using fully offline processing.
    
    Returns medical answers grounded in retrieved context with source attribution.
    Uses local SentenceTransformer embeddings - NO external API keys required.
    
    - Rate limited to 20/minute per IP
    - Fully offline operation (no OpenAI API calls)
    - Uses ChromaDB vector database and local embeddings
    
    Args:
        question: Medical question to answer
        disease_type: Optional disease type filter 
                     (dermatology, lung_cancer, breast_cancer, 
                      diabetic_retinopathy, general_diseases)
    
    Returns:
        RAGChatResponse with answer, sources, and metadata
    """
    logger.info(f"[ROUTE] Local RAG Chat Request - Question: {chat_request.question[:100]}, Disease: {chat_request.disease_type}")
    
    try:
        # Use cached RAG pipeline from chatbot service (loaded once at startup)
        from app.services.chatbot_service import _get_rag_pipeline
        
        pipeline = _get_rag_pipeline()
        if pipeline is None:
            logger.error("[ROUTE] RAG Pipeline not available")
            return RAGChatResponse(
                answer="",
                sources=[],
                retrieved_count=0,
                model="local",
                error="RAG system unavailable. The medical knowledge base could not be loaded."
            )
        
        logger.debug("[ROUTE] Using cached RAG pipeline instance")
        
        # Generate answer using local processing only
        result = pipeline.generate_answer(
            query=chat_request.question,
            disease_type=chat_request.disease_type,
            top_k=5
        )
        
        # Convert sources to SourceMetadata objects
        sources = [
            SourceMetadata(
                id=source["id"],
                collection=source["collection"],
                source_file=source["source_file"],
                relevance_score=source["relevance_score"],
                preview=source["preview"]
            )
            for source in result.get("sources", [])
        ]
        
        # Build response
        response = RAGChatResponse(
            answer=result.get("answer", ""),
            sources=sources,
            retrieved_count=result.get("retrieved_count", 0),
            model=result.get("model", "local"),
            error=result.get("error")
        )
        
        logger.info(
            f"[ROUTE] ✅ Local RAG Chat Success - Answer length: {len(response.answer)}, "
            f"Sources: {len(response.sources)}, Retrieved: {response.retrieved_count}"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"[ROUTE] Local RAG Chat Error: {str(e)}", exc_info=True)
        return RAGChatResponse(
            answer="",
            sources=[],
            retrieved_count=0,
            model="local",
            error=f"Error generating response: {str(e)}"
        )


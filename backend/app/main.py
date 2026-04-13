import logging
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import engine
from app.rate_limiter import limiter
from app.routes import auth, diagnosis, risk, report, hospitals, chatbot, health
from app.services.ml_service import get_model_status


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("medintel.api")

app = FastAPI(
    title="MedIntel API",
    description="Multi-Disease AI Diagnostic Assistant API",
    version="1.0.0",
)

# ============================================================================
# CRITICAL: Add CORS Middleware FIRST (before all other middleware)
# ============================================================================
logger.info("🚀 =================== MedIntel API Starting ===================")
logger.info("🌐 CORS Configuration:")
cors_origins = settings.ALLOWED_ORIGINS or ["http://localhost:8080"]
logger.info(f"   Allowed origins: {cors_origins}")
logger.info("   Credentials: enabled")
logger.info("   Methods: *")
logger.info("   Headers: *")
logger.info("   Max-Age: 3600")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

logger.info("\n🌍 Frontend URL: http://localhost:8080")
logger.info("🔧 Backend URL: http://localhost:8000")
logger.info("\n📋 Available Endpoints:")
logger.info("   Diagnosis:")
logger.info("      - Lung Cancer: POST /api/v1/diagnosis/lung-cancer")
logger.info("      - Skin Disease: POST /api/v1/diagnosis/skin-disease")
logger.info("      - Diabetic Retinopathy: POST /api/v1/diagnosis/diabetic-retinopathy")
logger.info("   Chatbot:")
logger.info("      - Message: POST /api/chatbot/message")
logger.info("      - RAG Chat: POST /api/chatbot/chat")
logger.info("      - Clear Session: DELETE /api/chatbot/session/{session_id}")
logger.info("   Health:")
logger.info("      - Health Check: GET /health")
logger.info("      - Readiness: GET /ready")
logger.info("      - Models Status: GET /api/v1/models/status")
logger.info("\n🐛 Debug Endpoints:")
logger.info("   - Config: GET /api/v1/debug/config")
logger.info("   - CORS Test: GET /api/v1/debug/cors-test")
logger.info("\n✅ API Ready!\n")


@app.on_event("startup")
async def startup_event():
    """Initialize RAG pipeline and other services on startup."""
    logger.info("[STARTUP] Initializing services...")
    try:
        from app.services.chatbot_service import _get_rag_pipeline
        try:
            pipeline = _get_rag_pipeline()
            if pipeline:
                logger.info("[STARTUP] ✅ RAG pipeline ready (will use cached instance)")
            else:
                logger.warning("[STARTUP] ⚠️  RAG pipeline not available")
        except Exception as e:
            logger.error(f"[STARTUP] ⚠️  RAG pipeline initialization skipped: {str(e)}", exc_info=False)
    except Exception as e:
        logger.error(f"[STARTUP] ❌ Startup error: {str(e)}", exc_info=True)


# ============================================================================
# Rate limiting middleware (add AFTER CORS)
# ============================================================================
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers_and_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception: %s %s - %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    duration_ms = (time.time() - start) * 1000
    log_data: Dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "response_time_ms": round(duration_ms, 2),
    }
    if 500 <= response.status_code < 600:
        logger.error("Request: %s", log_data)
    else:
        logger.info("Request: %s", log_data)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input",
            "details": exc.errors(),
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid input",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server error at %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(diagnosis.router, prefix="/api/v1", tags=["diagnosis"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(report.router, prefix="/api/v1", tags=["report"])
app.include_router(hospitals.router, prefix="/api/v1", tags=["hospitals"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready")
async def readiness():
    db_ok = True
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("Database connection failed: %s", str(e))
        db_ok = False

    models = get_model_status()
    status_code = 200
    return JSONResponse(
        status_code=status_code,
        content={
            "db_ok": db_ok,
            "models": models,
        },
    )


@app.get("/api/v1/models/status")
async def models_status():
    return get_model_status()


@app.get("/api/v1/debug/config")
async def debug_config():
    return {
        "api": {
            "title": app.title,
            "version": app.version,
            "description": app.description
        },
        "cors": {
            "allowed_origins": settings.ALLOWED_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        },
        "ml_models": get_model_status(),
        "frontend_url": "http://localhost:8080",
        "backend_url": "http://localhost:8000"
    }


@app.get("/api/v1/debug/cors-test")
async def cors_test(request: Request):
    return {
        "cors_status": "OK",
        "origin": request.headers.get("origin", "No origin header"),
        "allowed": True
    }
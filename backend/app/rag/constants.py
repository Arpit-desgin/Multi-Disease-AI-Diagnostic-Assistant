"""
Global constants for RAG system configuration.

This centralized constants file ensures consistency across:
- Vector store initialization
- Data ingestion
- Document retrieval
- RAG pipeline
"""

from pathlib import Path
import logging

logger = logging.getLogger("app.rag.constants")

# Get the absolute path to the RAG directory (where this file is located)
RAG_DIR = Path(__file__).parent

# CRITICAL: Single source of truth for ChromaDB persistent storage
CHROMA_DB_PATH = RAG_DIR / "chroma_data"

# Data directory for ingestion
DATA_DIR = RAG_DIR / "Data"

logger.info(f"[CONSTANTS] RAG_DIR: {RAG_DIR}")
logger.info(f"[CONSTANTS] CHROMA_DB_PATH: {CHROMA_DB_PATH}")
logger.info(f"[CONSTANTS] DATA_DIR: {DATA_DIR}")

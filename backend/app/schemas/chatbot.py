"""
Pydantic schemas for RAG chatbot API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Schema for chatbot input request."""
    question: str = Field(..., min_length=1, description="Medical question to answer")
    disease_type: Optional[str] = Field(
        None,
        description="Optional disease type filter: dermatology, lung_cancer, breast_cancer, general_diseases"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the symptoms of melanoma?",
                "disease_type": "dermatology"
            }
        }


class ChatResponse(BaseModel):
    """Schema for chatbot output response."""
    answer: str = Field(..., description="Generated medical answer")
    sources: List[str] = Field(default_factory=list, description="List of source document IDs used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Melanoma symptoms include...",
                "sources": ["doc_123", "doc_456"]
            }
        }

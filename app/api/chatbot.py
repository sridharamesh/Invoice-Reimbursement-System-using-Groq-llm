from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.core.vector_store import query_vector_store
from app.core.rag_utils import answer_query_with_context

router = APIRouter()

class ChatQuery(BaseModel):
    question: str
    filters: Optional[Dict[str, Any]] = None
    max_docs: Optional[int] = 5

class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    num_sources: int

@router.post("/chat", response_model=ChatResponse)
async def rag_chat(query: ChatQuery):
    if not query.question:
        raise HTTPException(status_code=400, detail="Empty question")
    
    docs = query_vector_store(query.question, filters=query.filters, top_k=query.max_docs or 5)
    
    if not docs:
        return ChatResponse(
            question=query.question,
            answer="No relevant information found.",
            sources=[],
            num_sources=0
        )
    
    answer = answer_query_with_context(query.question, docs)
    return ChatResponse(
        question=query.question,
        answer=answer,
        sources=[doc["metadata"] for doc in docs],
        num_sources=len(docs)
    )

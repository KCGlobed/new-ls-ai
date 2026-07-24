from typing import Optional, List
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    session_id: str
    document_ids: Optional[List[str]] = None
    user_id: Optional[str] = None

class CitationSchema(BaseModel):
    id: int
    file_name: str
    document_id: Optional[str] = None
    page_or_row: int | str
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationSchema]
    metrics: dict

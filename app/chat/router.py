import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from app.audit import AuditEvent, write_audit
from app.database.dependencies import get_db, get_lms_db
from app.chat.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import RAGPipeline
from app.rag.memory.long_term import LongTermMemory
from app.database.models.conversation import Conversation

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger(__name__)

import json
from fastapi.responses import StreamingResponse

@router.post("/")
async def chat_endpoint(
    chat_req: ChatRequest,
    request: Request,
    userId: str = Query(..., description="LMS user ID passed from the host application"),
    db: Session = Depends(get_db),
    lms_db: Session = Depends(get_lms_db),
):
    """
    Public endpoint for the chat widget. No authorization headers required.
    userId is passed as a query string parameter from the host LMS.
    Returns a Server-Sent Events (SSE) stream.
    """
    structlog.contextvars.bind_contextvars(
        user_id=userId,
        session_id=chat_req.session_id,
    )
    
    logger.info("chat_request_received", query_length=len(chat_req.query))
    write_audit(
        db,
        AuditEvent.RAG_QUERY_STARTED,
        status="success",
        user_id=userId,
        user_email="lms_user",
        details={"session_id": chat_req.session_id}
    )

    # Fetch long-term memory history for this session (from our DB)
    memory = LongTermMemory(db)
    # 15 messages is a great sweet spot for context (approx 7-8 turns)
    history = memory.get_session_history(chat_req.session_id, limit=15)

    async def generate():
        pipeline = RAGPipeline()
        try:
            async for chunk in pipeline.run(
                query=chat_req.query,
                user_id=userId,
                history=history,
                db=db,
                lms_db=lms_db,
                document_ids=chat_req.document_ids
            ):
                if isinstance(chunk, str):
                    # Yield text chunk as SSE data
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                elif isinstance(chunk, dict):
                    # Final metadata dict
                    # Save the new turn to history (in our DB)
                    memory.save_turn(
                        session_id=chat_req.session_id,
                        user_id=userId,
                        user_msg=chat_req.query,
                        ai_msg=chunk.get("answer", "")
                    )

                    write_audit(
                        db,
                        AuditEvent.RAG_QUERY_SUCCESS,
                        status="success",
                        user_id=userId,
                        user_email="lms_user",
                        details={
                            "session_id": chat_req.session_id,
                            "metrics": chunk.get("metrics", {}),
                            "citations": len(chunk.get("citations", []))
                        }
                    )
                    
                    # Yield special metadata event
                    yield f"event: metadata\n"
                    yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as exc:
            logger.error("chat_request_failed", exc_info=True, error=str(exc))
            write_audit(
                db,
                AuditEvent.RAG_QUERY_FAILURE,
                status="failure",
                user_id=userId,
                user_email="lms_user",
                details={"session_id": chat_req.session_id},
                error_message=str(exc)
            )
            yield f"data: {json.dumps({'chunk': 'An error occurred while answering your question.'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/history")
def get_chat_history(
    userId: str = Query(..., description="LMS user ID"),
    db: Session = Depends(get_db)
):
    """
    Returns a list of all chat sessions for the given user, ordered by most recent.
    Acts like the ChatGPT sidebar history.
    """
    # Fetch all user messages for this user, ordered by oldest first 
    # (so we capture the very first message as the title)
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == userId, Conversation.role == "user")
        .order_by(Conversation.created_at.asc())
        .all()
    )
    
    # Group by session_id in Python to get unique sessions and their first message
    sessions_map = {}
    for conv in conversations:
        if conv.session_id not in sessions_map:
            # Create a short title from the first message
            title = conv.content
            if len(title) > 40:
                title = title[:40] + "..."
                
            sessions_map[conv.session_id] = {
                "session_id": conv.session_id,
                "title": title,
                "created_at": conv.created_at.isoformat()
            }
        else:
            # We also update the created_at to the latest message so we can sort by most recent activity
            sessions_map[conv.session_id]["updated_at"] = conv.created_at.isoformat()
            
    # Sort sessions by newest first
    sorted_sessions = sorted(
        sessions_map.values(), 
        key=lambda x: x.get("updated_at", x["created_at"]), 
        reverse=True
    )
    
    return {"sessions": sorted_sessions}

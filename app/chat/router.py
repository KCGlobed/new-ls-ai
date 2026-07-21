import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.audit import AuditEvent, write_audit
from app.database.dependencies import get_db
from app.database.models.users import Users
from app.chat.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import RAGPipeline
from app.rag.memory.long_term import LongTermMemory

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger(__name__)


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    chat_req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    structlog.contextvars.bind_contextvars(
        user_id=str(current_user.id),
        session_id=chat_req.session_id,
    )
    
    logger.info("chat_request_received", query_length=len(chat_req.query))
    write_audit(
        db,
        AuditEvent.RAG_QUERY_STARTED,
        status="success",
        user_id=str(current_user.id),
        user_email=current_user.email,
        details={"session_id": chat_req.session_id}
    )

    try:
        # Fetch long-term memory history for this session
        memory = LongTermMemory(db)
        history = memory.get_session_history(chat_req.session_id, limit=6)

        # Run pipeline
        pipeline = RAGPipeline()
        answer_data, metrics = await pipeline.run(
            query=chat_req.query,
            user_id=str(current_user.id),
            history=history,
            db=db,
            document_ids=chat_req.document_ids
        )

        # Save the new turn to history
        memory.save_turn(
            session_id=chat_req.session_id,
            user_id=str(current_user.id),
            user_msg=chat_req.query,
            ai_msg=answer_data["answer"]
        )

        write_audit(
            db,
            AuditEvent.RAG_QUERY_SUCCESS,
            status="success",
            user_id=str(current_user.id),
            user_email=current_user.email,
            details={
                "session_id": chat_req.session_id,
                "metrics": metrics,
                "citations": len(answer_data.get("citations", []))
            }
        )

        return ChatResponse(
            answer=answer_data["answer"],
            citations=answer_data["citations"],
            metrics=metrics
        )

    except Exception as exc:
        logger.error("chat_request_failed", exc_info=True, error=str(exc))
        write_audit(
            db,
            AuditEvent.RAG_QUERY_FAILURE,
            status="failure",
            user_id=str(current_user.id),
            user_email=current_user.email,
            details={"session_id": chat_req.session_id},
            error_message=str(exc)
        )
        # Raise generic 500 error or return a friendly fallback message
        # We will return the fallback answer to preserve user experience
        return ChatResponse(
            answer="An error occurred while answering your question. Please try again.",
            citations=[],
            metrics={}
        )

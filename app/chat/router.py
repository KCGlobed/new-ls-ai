import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from app.audit import AuditEvent, write_audit
from app.database.dependencies import get_db, get_lms_db
from app.chat.schemas import ChatRequest, ChatResponse
from app.rag.pipeline import RAGPipeline
from app.rag.memory.long_term import LongTermMemory

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger(__name__)


@router.post("/", response_model=ChatResponse)
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

    try:
        # Fetch long-term memory history for this session (from our DB)
        memory = LongTermMemory(db)
        history = memory.get_session_history(chat_req.session_id, limit=6)

        # Run pipeline
        pipeline = RAGPipeline()
        answer_data, metrics = await pipeline.run(
            query=chat_req.query,
            user_id=userId,
            history=history,
            db=db,
            lms_db=lms_db,
            document_ids=chat_req.document_ids
        )

        # Save the new turn to history (in our DB)
        memory.save_turn(
            session_id=chat_req.session_id,
            user_id=userId,
            user_msg=chat_req.query,
            ai_msg=answer_data["answer"]
        )

        write_audit(
            db,
            AuditEvent.RAG_QUERY_SUCCESS,
            status="success",
            user_id=userId,
            user_email="lms_user",
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
            user_id=userId,
            user_email="lms_user",
            details={"session_id": chat_req.session_id},
            error_message=str(exc)
        )
        return ChatResponse(
            answer="An error occurred while answering your question. Please try again.",
            citations=[],
            metrics={}
        )

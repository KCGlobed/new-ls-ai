import structlog
from sqlalchemy.orm import Session
from app.database.models.conversation import Conversation

logger = structlog.get_logger(__name__)

class LongTermMemory:
    def __init__(self, db: Session):
        self.db = db

    def save_turn(self, session_id: str, user_id: str, user_msg: str, ai_msg: str) -> None:
        """Saves a single question and answer turn to the database."""
        try:
            for role, content in [("user", user_msg), ("assistant", ai_msg)]:
                turn = Conversation(
                    session_id=session_id, 
                    user_id=user_id, 
                    role=role, 
                    content=content
                )
                self.db.add(turn)
            self.db.commit()
            logger.info("conversation_turn_saved", session_id=session_id)
        except Exception as exc:
            self.db.rollback()
            logger.error("failed_to_save_conversation", exc_info=True, error=str(exc))

    def get_session_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """Retrieves the last N messages for a given session."""
        try:
            turns = (
                self.db.query(Conversation)
                .filter(Conversation.session_id == session_id)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
                .all()
            )
            # Re-order to chronological
            history = [{"role": t.role, "content": t.content} for t in reversed(turns)]
            return history
        except Exception as exc:
            logger.error("failed_to_fetch_history", exc_info=True, error=str(exc))
            return []

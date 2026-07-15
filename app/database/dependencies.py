from app.database.session import SessionLocal
from sqlalchemy.orm import Session
from collections.abc import Generator
def get_db()->Generator[Session,None,None]:
    db=SessionLocal()

    try:
        yield db
    finally:
        db.close()

        
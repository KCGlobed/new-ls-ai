from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.dependencies import get_db
from app.database.models.users import Users

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Fixed system user UUID used by the chat widget (no real user account needed)
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


class SystemUser:
    """Lightweight stand-in returned when the widget system token is used."""
    id = SYSTEM_USER_ID
    email = "system@lms-widget"


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    # If the token belongs to the widget system user, skip the DB lookup
    if user_id == SYSTEM_USER_ID:
        return SystemUser()

    user = db.query(Users).filter(Users.id == str(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

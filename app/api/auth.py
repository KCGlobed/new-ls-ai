from datetime import timedelta

import structlog
import structlog.contextvars
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import AuditEvent, write_audit
from app.core import security
from app.core.config import settings
from app.database.dependencies import get_db
from app.database.models.users import Users
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger(__name__)


@router.post("/register", response_model=UserResponse)
def register_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    # Bind user email to log context for this request
    structlog.contextvars.bind_contextvars(email=user_in.email)

    existing = db.query(Users).filter(Users.email == user_in.email).first()
    if existing:
        logger.warning("register_duplicate_email", email=user_in.email)
        write_audit(
            db,
            AuditEvent.USER_REGISTER_FAILURE,
            status="failure",
            user_email=user_in.email,
            error_message="Email already registered",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )

    hashed_password = security.get_password_hash(user_in.password)
    user = Users(email=user_in.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("register_success", user_id=str(user.id), email=user.email)
    write_audit(
        db,
        AuditEvent.USER_REGISTER_SUCCESS,
        status="success",
        user_id=str(user.id),
        user_email=user.email,
    )
    return user


@router.post("/login", response_model=Token)
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    structlog.contextvars.bind_contextvars(email=form_data.username)

    user = db.query(Users).filter(Users.email == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        logger.warning("login_failed", email=form_data.username)
        write_audit(
            db,
            AuditEvent.USER_LOGIN_FAILURE,
            status="failure",
            user_email=form_data.username,
            error_message="Invalid email or password",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    logger.info("login_success", user_id=str(user.id), email=user.email)
    write_audit(
        db,
        AuditEvent.USER_LOGIN_SUCCESS,
        status="success",
        user_id=str(user.id),
        user_email=user.email,
    )
    return {"access_token": access_token, "token_type": "bearer"}

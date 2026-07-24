import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.request_logger import RequestLoggerMiddleware

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.chat.router import router as chat_router

# ── 1. Setup structured logging (must be first) ────────────────────────────
log_level = "INFO" if settings.app_env != "production" else "WARNING"
setup_logging(log_level=log_level)
logger = structlog.get_logger(__name__)

# ── 2. Create FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Enterprise LMS AI Backend with RAG pipeline",
    version="0.1.0",
)

# ── 3. Register middleware (order matters — outermost first) ───────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://lms-dev-v2.web.app",
        "https://pro.kcglobed.com",
        "https://new-lms-ai-frontend-233960786746.europe-west1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggerMiddleware)

# ── 4. Register routers ────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(chat_router)


# ── 5. Startup event ───────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "system.startup",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

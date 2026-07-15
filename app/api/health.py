from app.database.dependencies import get_db
from fastapi import APIRouter,Depends
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import text
router=APIRouter()


@router.get("/")
def health(db:Session=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "app_name":settings.app_name,
        "app_env":settings.app_env,
        "status":"ok"
    }





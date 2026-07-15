from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class UploadResponse(BaseModel):
    id:str
    title:str
    original_filename: str
    storage_path: str
    status: str
    uploaded_at: datetime
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentMeta(BaseModel):
    document_id: str
    filename: str
    raw_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    scope_type: str
    owner_id: str
    team_id: Optional[str] = None

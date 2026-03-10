from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SpaceType(str, Enum):
    personal = "personal"
    team = "team"


class ProcessDocumentRequest(BaseModel):
    document_id: str
    file_url: str
    user_id: str
    space_type: SpaceType
    space_id: Optional[str] = None

class DeleteDocumentRequest(BaseModel):
    user_id: str
    space_type: SpaceType
    space_id: Optional[str] = None
from pydantic import BaseModel, Field
from typing import Literal, Optional


class Scope(BaseModel):
    scope_type: Literal["personal", "team"] = Field(
        ..., description="Defines whether the request is personal or team scoped"
    )
    owner_id: str = Field(
        ..., description="User ID of the owner (always present)"
    )
    team_id: Optional[str] = Field(
        None, description="Team ID if scope_type is team"
    )

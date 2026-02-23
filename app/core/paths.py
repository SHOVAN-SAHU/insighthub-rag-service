from pathlib import Path
from app.schemas.common import Scope

BASE_STORAGE = Path(__file__).parent.parent / "storage"


def resolve_scope_path(scope: Scope) -> Path:
    if scope.scope_type == "personal":
        return BASE_STORAGE / "personal" / scope.owner_id

    if scope.scope_type == "team":
        if not scope.team_id:
            raise ValueError("team_id is required for team scope")
        return BASE_STORAGE / "team" / scope.team_id

    raise ValueError(f"Invalid scope_type: {scope.scope_type}")

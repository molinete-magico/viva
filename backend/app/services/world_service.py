from sqlmodel import Session

from app.database.seed import ensure_world_state
from app.models import WorldState


def get_world(session: Session) -> WorldState:
    return ensure_world_state(session)

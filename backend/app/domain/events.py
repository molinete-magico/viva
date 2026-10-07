from __future__ import annotations

from app.domain.errors import ServiceError

EVENT_SCHEDULED = "SCHEDULED"
EVENT_OPEN = "OPEN"
EVENT_ACTIVE = "ACTIVE"
EVENT_COMPLETED = "COMPLETED"
EVENT_CANCELLED = "CANCELLED"

PARTICIPANT_INVITED = "INVITED"
PARTICIPANT_ACCEPTED = "ACCEPTED"
PARTICIPANT_DECLINED = "DECLINED"
PARTICIPANT_WITHDREW = "WITHDREW"
PARTICIPANT_JOINED = "JOINED"

SESSION_ACTIVE = "ACTIVE"
SESSION_COMPLETED = "COMPLETED"
SESSION_ABANDONED = "ABANDONED"

_EVENT_TRANSITIONS: dict[str, dict[str, str]] = {
    EVENT_SCHEDULED: {"open": EVENT_OPEN, "start": EVENT_ACTIVE, "cancel": EVENT_CANCELLED},
    EVENT_OPEN: {"start": EVENT_ACTIVE, "cancel": EVENT_CANCELLED},
    EVENT_ACTIVE: {"complete": EVENT_COMPLETED, "cancel": EVENT_CANCELLED},
    EVENT_COMPLETED: {},
    EVENT_CANCELLED: {},
}

_PARTICIPANT_TRANSITIONS: dict[str, dict[str, str]] = {
    PARTICIPANT_INVITED: {"accept": PARTICIPANT_ACCEPTED, "decline": PARTICIPANT_DECLINED},
    PARTICIPANT_ACCEPTED: {"join": PARTICIPANT_JOINED, "withdraw": PARTICIPANT_WITHDREW},
    PARTICIPANT_JOINED: {"withdraw": PARTICIPANT_WITHDREW},
    PARTICIPANT_DECLINED: {"accept": PARTICIPANT_ACCEPTED},
    PARTICIPANT_WITHDREW: {},
}

_SESSION_TRANSITIONS: dict[str, dict[str, str]] = {
    SESSION_ACTIVE: {"complete": SESSION_COMPLETED, "abandon": SESSION_ABANDONED},
    SESSION_COMPLETED: {},
    SESSION_ABANDONED: {},
}

DIMENSIONS = ("familiarity", "friendship", "trust", "romance", "respect", "tension")

MAX_EVENT_ACTIONS = 5
MAX_TURNS = 30
MAX_TURN_LENGTH = 8000


def transition_event(status: str, action: str) -> str:
    allowed = _EVENT_TRANSITIONS.get(status, {})
    if action not in allowed:
        raise ServiceError(f"Não é possível {action} um evento {status}.", 409)
    return allowed[action]


def transition_participant(status: str, action: str) -> str:
    allowed = _PARTICIPANT_TRANSITIONS.get(status, {})
    if action not in allowed:
        raise ServiceError(f"Você não pode fazer isso agora (status {status}).", 409)
    return allowed[action]


def transition_session(status: str, action: str) -> str:
    allowed = _SESSION_TRANSITIONS.get(status, {})
    if action not in allowed:
        raise ServiceError(f"A sessão está {status} e não permite {action}.", 409)
    return allowed[action]
from datetime import datetime

from pydantic import BaseModel, Field


class EventOut(BaseModel):
    id: int
    title: str
    description: str
    scheduled_at: datetime | None = None
    status: str
    kind: str
    location_id: int
    location_name: str = ""
    host_character_id: int | None = None
    host_name: str = ""
    participant_count: int = 0
    my_status: str | None = None
    cancel_reason: str | None = None


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    location_id: int
    scheduled_at: datetime | None = None
    kind: str = Field(default="social", max_length=32)
    invite_conversation_ids: list[int] = Field(default_factory=list)


class RSVPRequest(BaseModel):
    accept: bool


class CancelEventRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class EventParticipantOut(BaseModel):
    character_id: int
    name: str
    status: str
    photo_url: str | None = None
    is_npc: bool = True


class EventDetailOut(EventOut):
    participants: list[EventParticipantOut] = Field(default_factory=list)
    am_host: bool = False


class TurnOut(BaseModel):
    id: int
    turn_index: int
    narrative: str
    dialogue: list
    available_actions: list
    player_action_id: str | None = None
    player_action_label: str | None = None
    created_at: datetime


class SessionSummaryOut(BaseModel):
    id: int
    event_id: int
    status: str
    turn_count: int
    resume_count: int
    started_at: datetime
    ended_at: datetime | None = None
    last_activity_at: datetime


class SessionStateOut(BaseModel):
    session: SessionSummaryOut
    turns: list[TurnOut] = Field(default_factory=list)
    can_act: bool
    outcome_id: int | None = None


class ActionRequest(BaseModel):
    action_id: str | None = Field(default=None, min_length=1, max_length=64)
    free_text: str | None = Field(default=None, min_length=1, max_length=1000)

    def model_post_init(self, __context) -> None:
        if not self.action_id and not self.free_text:
            raise ValueError("Informe uma ação ou descreva o que deseja fazer.")


class OutcomeOut(BaseModel):
    id: int
    session_id: int
    summary: str
    relationship_changes: list
    memories: list
    social_effects: list
    future_hooks: list
    applied_at: datetime
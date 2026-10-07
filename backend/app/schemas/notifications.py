from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    type: str
    payload: dict
    created_at: datetime
    read_at: datetime | None = None


class ReadResultOut(BaseModel):
    ok: bool = True

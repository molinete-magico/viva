from datetime import date, datetime

from pydantic import BaseModel

from app.models import WorldState

DAY_NAMES = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]


class WorldOut(BaseModel):
    city_name: str
    date: date
    time: str
    day_of_week: int
    day_name: str
    last_simulated_at: datetime
    last_catchup_at: datetime | None = None


def world_out(state: WorldState) -> WorldOut:
    return WorldOut(
        city_name=state.city_name,
        date=state.current_date,
        time=state.current_time,
        day_of_week=state.current_date.weekday(),
        day_name=DAY_NAMES[state.current_date.weekday()],
        last_simulated_at=state.last_simulated_at,
        last_catchup_at=state.last_catchup_at,
    )

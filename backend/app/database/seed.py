import logging
from datetime import date

from sqlmodel import Session, select

from app.database.session import engine
from app.models import MilestoneProgress, StoryMilestone, WorldState
from app.models.base import utcnow
from app.database.seed_photos import ensure_npc_photos
from app.database.seed_world import run_world_seed

logger = logging.getLogger("viva.seed")

DEFAULT_MILESTONES = [
    {
        "key": "character_unlock",
        "name": "Novo rosto na cidade",
        "description": "A cada 5 eventos significativos concluídos, surge a oportunidade de criar um novo personagem.",
        "threshold": 5,
    }
]


def ensure_world_state(session: Session) -> WorldState:
    state = session.get(WorldState, 1)
    if state is None:
        state = WorldState(
            id=1,
            current_date=date.today(),
            current_time="08:00",
            last_simulated_at=utcnow(),
            last_catchup_at=None,
        )
        session.add(state)
        session.commit()
        session.refresh(state)
        logger.info("world state created")
    return state


def ensure_milestones(session: Session) -> None:
    from app.services.milestone_service import MILESTONES as EXTRA_MILESTONES

    for data in [*EXTRA_MILESTONES, *DEFAULT_MILESTONES]:
        existing = session.exec(select(StoryMilestone).where(StoryMilestone.key == data["key"])).first()
        if existing is None:
            session.add(StoryMilestone(**data))
        progress = session.exec(select(MilestoneProgress).where(MilestoneProgress.key == data["key"])).first()
        if progress is None:
            session.add(MilestoneProgress(key=data["key"]))
    session.commit()


def run_seed() -> None:
    with Session(engine) as session:
        ensure_world_state(session)
        ensure_milestones(session)
        run_world_seed(session)
        ensure_npc_photos(session)
    logger.info("seed applied")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_seed()
    print("seed applied")

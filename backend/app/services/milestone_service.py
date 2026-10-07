from __future__ import annotations

from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.models import MilestoneProgress, StoryMilestone
from app.models.base import utcnow

MILESTONES: list[dict] = [
    {
        "key": "FIRST_MEETING",
        "name": "Primeiro contato",
        "description": "Apresente-se nas horas certas da cidade.",
        "threshold": 2,
    },
    {
        "key": "NEW_MEMORY",
        "name": "Memórias em construção",
        "description": "Acumule bons momentos que ficam na memória.",
        "threshold": 3,
    },
    {
        "key": "LONG_CONVERSATION",
        "name": "Boa conversa",
        "description": "Role uma conversa longa com alguém da cidade.",
        "threshold": 4,
    },
    {
        "key": "EVENT_PARTICIPATION",
        "name": "Vida social",
        "description": "Participe de eventos e marque presença.",
        "threshold": 2,
    },
    {
        "key": "FIVE_FOLLOWERS",
        "name": "Quem olha seu feed",
        "description": "Alcance cinco quem acompanha sua rotina.",
        "threshold": 5,
    },
    {
        "key": "TWENTY_POSTS",
        "name": "Voz ativa",
        "description": "Publique regularmente na cidade.",
        "threshold": 20,
    },
]


def ensure_milestones(session: Session) -> None:
    for data in MILESTONES:
        existing = session.exec(select(StoryMilestone).where(StoryMilestone.key == data["key"])).first()
        if existing is None:
            session.add(StoryMilestone(**data))
    session.commit()


def list_milestones(session: Session) -> list[dict]:
    ensure_milestones(session)
    milestones = session.exec(
        select(StoryMilestone).order_by(StoryMilestone.threshold)
    ).all()
    progress_rows = {
        p.key: p for p in session.exec(select(MilestoneProgress)).all()
    }
    items = []
    for milestone in milestones:
        progress = progress_rows.get(milestone.key)
        items.append(
            {
                "key": milestone.key,
                "name": milestone.name,
                "description": milestone.description,
                "threshold": milestone.threshold,
                "count": progress.qualifying_count if progress else 0,
                "pending": progress.pending_opportunity if progress else False,
                "last_opportunity_at": progress.last_opportunity_at if progress else None,
            }
        )
    return items


def record_progress(session: Session, key: str, amount: int = 1) -> MilestoneProgress:
    milestone = session.exec(select(StoryMilestone).where(StoryMilestone.key == key)).first()
    if milestone is None:
        return None
    progress = session.exec(select(MilestoneProgress).where(MilestoneProgress.key == key)).first()
    if progress is None:
        progress = MilestoneProgress(key=key)
        session.add(progress)
    progress.qualifying_count += max(1, amount)
    if progress.qualifying_count >= milestone.threshold and progress.qualifying_count % milestone.threshold == 0:
        progress.pending_opportunity = True
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def claim(session: Session, key: str, owner: "Character", *, reward: float = 80.0) -> dict:
    from app.models import Character

    milestone = session.exec(select(StoryMilestone).where(StoryMilestone.key == key)).first()
    if milestone is None:
        raise ServiceError("Marco não encontrado.", 404)
    progress = session.exec(select(MilestoneProgress).where(MilestoneProgress.key == key)).first()
    if progress is None or not progress.pending_opportunity:
        raise ServiceError(
            "Ainda não há uma oportunidade para resgatar. Continue vivendo na Vila Serena.",
            409,
        )
    progress.pending_opportunity = False
    progress.last_opportunity_at = utcnow()
    owner.money = round((owner.money or 0) + reward, 2)
    session.add(progress)
    session.add(owner)
    session.commit()
    return {
        "key": key,
        "name": milestone.name,
        "reward": reward,
        "last_opportunity_at": progress.last_opportunity_at,
    }
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database.session import get_session
from app.domain.errors import ServiceError
from app.models import Notification, User
from app.schemas.common import Listing
from app.schemas.notifications import NotificationOut, ReadResultOut
from app.models.base import utcnow

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Listing[NotificationOut])
def list_notifications(
    unread: bool | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.active_character_id is None:
        return Listing(items=[])
    query = (
        select(Notification)
        .where(Notification.character_id == user.active_character_id)
    )
    if unread is True:
        query = query.where(Notification.read_at.is_(None))
    elif unread is False:
        query = query.where(Notification.read_at.is_not(None))
    rows = session.exec(query.order_by(Notification.id.desc()).limit(50)).all()
    return Listing(
        items=[
            NotificationOut(
                id=n.id,
                type=n.type,
                payload=n.payload,
                created_at=n.created_at,
                read_at=n.read_at,
            )
            for n in rows
        ]
    )


@router.post("/{notification_id}/read", response_model=ReadResultOut)
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.active_character_id is None:
        raise ServiceError("Crie seu personagem para continuar.", 403)
    notification = session.get(Notification, notification_id)
    if notification is None or notification.character_id != user.active_character_id:
        raise ServiceError("Notificação não encontrada.", 404)
    if notification.read_at is None:
        notification.read_at = utcnow()
        session.add(notification)
        session.commit()
    return ReadResultOut(ok=True)


@router.post("/read-all", response_model=ReadResultOut)
def mark_all_read(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.active_character_id is None:
        raise ServiceError("Crie seu personagem para continuar.", 403)
    unread = session.exec(
        select(Notification).where(
            Notification.character_id == user.active_character_id,
            Notification.read_at.is_(None),
        )
    ).all()
    for notification in unread:
        notification.read_at = utcnow()
        session.add(notification)
    session.commit()
    return ReadResultOut(ok=True)
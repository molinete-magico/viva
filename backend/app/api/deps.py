from fastapi import Depends, Header
from sqlmodel import Session

from app.auth.security import decode_access_token
from app.database.session import get_session
from app.domain.errors import ServiceError
from app.models import User


def get_current_user(
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ServiceError("Faça login para continuar.", 401)
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_access_token(token)
    if user_id is None:
        raise ServiceError("Sessão expirada. Entre novamente.", 401)
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise ServiceError("Sessão inválida.", 401)
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise ServiceError("Você não tem permissão para isso.", 403)
    return user

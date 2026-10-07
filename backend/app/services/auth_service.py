from sqlmodel import func, select
from sqlmodel import Session

from app.auth.security import hash_password, verify_password
from app.domain.errors import ServiceError
from app.models import User


def register(session: Session, email: str, password: str) -> User:
    normalized = email.strip().lower()
    existing = session.exec(select(User).where(User.email == normalized)).first()
    if existing is not None:
        raise ServiceError("Já existe uma conta com esse e-mail.", 409)
    count = session.exec(select(func.count()).select_from(User)).first() or 0
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        is_admin=count == 0,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login(session: Session, email: str, password: str) -> User:
    normalized = email.strip().lower()
    user = session.exec(select(User).where(User.email == normalized)).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise ServiceError("E-mail ou senha incorretos.", 401)
    return user

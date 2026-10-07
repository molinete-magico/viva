from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.auth.security import create_access_token
from app.database.session import get_session
from app.models import Character, User
from app.schemas.auth import AuthResponse, LoginRequest, MeResponse, RegisterRequest, character_out, user_out
from app.services import auth_service, character_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, session: Session = Depends(get_session)):
    user = auth_service.register(session, req.email, req.password)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user_out(user))


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, session: Session = Depends(get_session)):
    user = auth_service.login(session, req.email, req.password)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user_out(user))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    active = None
    if user.active_character_id is not None:
        character = session.get(Character, user.active_character_id)
        if character is not None:
            photos = character_service.photo_url_map(session, [character])
            active = character_out(character, photo_url=photos.get(character.id))
    return MeResponse(user=user_out(user), active_character=active)

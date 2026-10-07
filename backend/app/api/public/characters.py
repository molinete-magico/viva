from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.database.session import get_session
from app.models import User
from app.schemas.character import CharacterDetailOut, CreateCharacterRequest, character_detail_out
from app.schemas.common import Listing
from app.schemas.auth import CharacterOut, character_out
from app.schemas.social import FeedResponse, FollowOut
from app.schemas.messaging import ConversationOut
from app.services import character_service, messaging_service, social_service

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=Listing[CharacterOut])
def list_characters(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    characters = character_service.list_characters(session)
    photos = character_service.photo_url_map(session, characters)
    items = [
        character_out(
            c,
            photo_url=photos.get(c.id),
            show_bio=character_service.can_view_bio(c, c.id == user.active_character_id),
        )
        for c in characters
    ]
    return Listing(items=items)


@router.post("", response_model=CharacterDetailOut, status_code=status.HTTP_201_CREATED)
def create_own_character(
    req: CreateCharacterRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.create_own(session, user, req)
    return character_detail_out(character, is_me=True, stats=character_service.stats_for(session, character.id))


@router.get("/{character_id}", response_model=CharacterDetailOut)
def get_character(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.get_character(session, character_id)
    is_me = character.id == user.active_character_id
    photos = character_service.photo_url_map(session, [character])
    stats = character_service.stats_for(session, character.id)
    is_following = (
        user.active_character_id is not None
        and social_service.is_following(session, user.active_character_id, character.id)
    )
    return character_detail_out(
        character,
        is_me=is_me,
        stats=stats,
        photo_url=photos.get(character.id),
        show_bio=character_service.can_view_bio(character, is_me),
        show_hobbies=character_service.can_view_details(character, is_me),
        is_following=is_following,
    )


@router.get("/{character_id}/posts", response_model=FeedResponse)
def character_posts(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character_service.get_character(session, character_id)
    return character_service.posts_by_character(session, character_id)


@router.post("/{character_id}/follow", response_model=FollowOut)
def follow_character(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    _, count = social_service.follow_character(session, actor, character_id)
    return FollowOut(following=True, followers_count=count)


@router.post("/{character_id}/dm", response_model=ConversationOut)
def start_dm(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    npc = character_service.get_character(session, character_id)
    conversation = messaging_service.get_or_create_conversation(session, actor, npc)
    messaging_service.ensure_active_session(session, conversation)
    from app.schemas.messaging import serialize_conversation

    return serialize_conversation(session, conversation, actor.id)


@router.delete("/{character_id}/follow", response_model=FollowOut)
def unfollow_character(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    social_service.unfollow_character(session, actor, character_id)
    return FollowOut(following=False, followers_count=social_service.follower_count(session, character_id))

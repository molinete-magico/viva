from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.models import Character, CharacterPhoto, Follow, Post, User
from app.schemas.character import CharacterStats, CreateCharacterRequest
from app.schemas.social import FeedResponse


def create_own(session: Session, user: User, req: CreateCharacterRequest) -> Character:
    if user.active_character_id is not None and session.get(Character, user.active_character_id) is not None:
        raise ServiceError("Você já tem um personagem na cidade.", 409)
    character = Character(
        user_id=user.id,
        name=req.name.strip(),
        age=req.age,
        pronouns=req.pronouns.strip(),
        bio=req.bio.strip(),
        profession_label=req.profession_label.strip(),
        is_npc=False,
        discovered_level=3,
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    user.active_character_id = character.id
    session.add(user)
    session.commit()
    session.refresh(user)
    return character


def get_active_character(session: Session, user: User) -> Character | None:
    if user.active_character_id is None:
        return None
    return session.get(Character, user.active_character_id)


def require_active_character(session: Session, user: User) -> Character:
    character = get_active_character(session, user)
    if character is None:
        raise ServiceError("Crie seu personagem para continuar.", 403)
    return character


def stats_for(session: Session, character_id: int) -> CharacterStats:
    posts = session.exec(select(Post).where(Post.author_character_id == character_id)).all()
    followers = session.exec(select(Follow).where(Follow.followed_character_id == character_id)).all()
    following = session.exec(select(Follow).where(Follow.follower_character_id == character_id)).all()
    return CharacterStats(posts=len(posts), followers=len(followers), following=len(following))


def list_characters(session: Session) -> list[Character]:
    return session.exec(select(Character).order_by(Character.id).limit(200)).all()


def get_character(session: Session, character_id: int) -> Character:
    character = session.get(Character, character_id)
    if character is None:
        raise ServiceError("Personagem não encontrado.", 404)
    return character


def posts_by_character(session: Session, character_id: int, limit: int = 20) -> FeedResponse:
    from app.services.feed_service import serialize_posts

    posts = session.exec(
        select(Post).where(Post.author_character_id == character_id).order_by(Post.id.desc()).limit(limit)
    ).all()
    return serialize_posts(session, posts, viewer=None)


def photo_url_map(session: Session, characters: list[Character]) -> dict[int, str]:
    photo_ids = [c.photo_id for c in characters if c.photo_id is not None]
    if not photo_ids:
        return {}
    photos = session.exec(select(CharacterPhoto).where(CharacterPhoto.id.in_(photo_ids))).all()
    return {photo.character_id: photo.path for photo in photos}


def can_view_bio(character: Character, is_me: bool) -> bool:
    if is_me or not character.is_npc:
        return True
    return character.discovered_level >= 2


def can_view_details(character: Character, is_me: bool) -> bool:
    if is_me or not character.is_npc:
        return True
    return character.discovered_level >= 3

def set_character_photo(session: Session, character: Character, data_url: str, photos_dir, stem: str) -> str:
    import base64
    import binascii
    from pathlib import Path
    if not data_url.startswith("data:image/"):
        raise ValueError("Envie uma imagem válida.")
    header, separator, encoded = data_url.partition(",")
    if not separator or not encoded:
        raise ValueError("Imagem inválida.")
    mime = header[5:].split(";")[0].lower()
    extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
    extension = extensions.get(mime)
    if extension is None:
        raise ValueError("Formato aceito: JPG, PNG, WEBP ou GIF.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Não foi possível ler a imagem.") from exc
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("A imagem deve ter no máximo 5 MB.")
    photos_dir = Path(photos_dir)
    photos_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{stem}{extension}"
    (photos_dir / filename).write_bytes(raw)
    old = session.exec(select(CharacterPhoto).where(CharacterPhoto.character_id == character.id)).all()
    for photo in old:
        photo.is_primary = False
        session.add(photo)
    photo = CharacterPhoto(character_id=character.id, source="upload", path=f"/static/photos/{filename}", label="perfil", is_primary=True)
    session.add(photo)
    session.commit()
    session.refresh(photo)
    character.photo_id = photo.id
    session.add(character)
    session.commit()
    return photo.path

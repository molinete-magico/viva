from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Character
from app.schemas.auth import CharacterOut, character_out


class UpdateCharacterRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    age: int | None = Field(default=None, ge=16, le=99)
    pronouns: str | None = Field(default=None, max_length=60)
    bio: str | None = Field(default=None, max_length=2000)
    profession_label: str | None = Field(default=None, max_length=120)


class CreateCharacterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=16, le=99)
    pronouns: str = Field(default="", max_length=60)
    bio: str = Field(default="", max_length=2000)
    profession_label: str = Field(default="", max_length=120)


class CharacterStats(BaseModel):
    posts: int = 0
    followers: int = 0
    following: int = 0


class CharacterDetailOut(CharacterOut):
    money: float | None = None
    stats: CharacterStats = Field(default_factory=CharacterStats)
    is_me: bool = False
    hobbies: list[str] = Field(default_factory=list)
    is_following: bool = False
    discovered_level: int = Field(default=1, ge=1, le=3)


def character_detail_out(
    character: Character,
    *,
    is_me: bool,
    stats: CharacterStats | None = None,
    photo_url: str | None = None,
    show_bio: bool = True,
    show_hobbies: bool = True,
    is_following: bool = False,
) -> CharacterDetailOut:
    base = character_out(character, photo_url=photo_url, show_bio=show_bio)
    return CharacterDetailOut(
        **base.model_dump(),
        money=character.money if is_me else None,
        stats=stats or CharacterStats(),
        is_me=is_me,
        hobbies=list(character.hobbies) if show_hobbies else [],
        is_following=is_following,
        discovered_level=character.discovered_level,
    )


__all__ = [
    "CharacterDetailOut",
    "CharacterOut",
    "CharacterStats",
    "CreateCharacterRequest",
    "UpdateCharacterRequest",
    "character_detail_out",
    "character_out",
]

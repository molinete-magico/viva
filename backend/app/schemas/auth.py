from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import Character, User


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool


class CharacterOut(BaseModel):
    id: int
    name: str
    age: int
    pronouns: str
    bio: str
    profession_label: str
    is_npc: bool
    photo_url: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut
    active_character: CharacterOut | None = None


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, is_admin=user.is_admin)


def character_out(
    character: Character,
    photo_url: str | None = None,
    show_bio: bool = True,
) -> CharacterOut:
    return CharacterOut(
        id=character.id,
        name=character.name,
        age=character.age,
        pronouns=character.pronouns,
        bio=character.bio if show_bio else "",
        profession_label=character.profession_label,
        is_npc=character.is_npc,
        photo_url=photo_url,
        created_at=character.created_at,
    )

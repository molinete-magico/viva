from datetime import datetime

from pydantic import BaseModel, Field


class AdminCharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=1, le=120)
    bio: str | None = Field(default=None, max_length=2000)
    profession_label: str | None = Field(default=None, max_length=120)
    is_npc: bool | None = None
    discovered_level: int | None = Field(default=None, ge=1, le=3)
    money: float | None = Field(default=None, ge=0)
    current_location_id: int | None = None
    personality: dict | None = None
    communication_style: str | None = None


class AdminCharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(default=20, ge=1, le=120)
    bio: str = Field(default="")
    profession_label: str = Field(default="", max_length=120)
    is_npc: bool = False
    discovered_level: int = Field(default=1)
    money: float = Field(default=0)


class AdminRelationshipUpdate(BaseModel):
    familiarity: int | None = Field(default=None, ge=-100, le=100)
    friendship: int | None = Field(default=None, ge=-100, le=100)
    trust: int | None = Field(default=None, ge=-100, le=100)
    romance: int | None = Field(default=None, ge=-100, le=100)
    respect: int | None = Field(default=None, ge=-100, le=100)
    tension: int | None = Field(default=None, ge=-100, le=100)


class AdminMemoryCreate(BaseModel):
    owner_character_id: int
    content: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="NORMAL", max_length=16)
    kind: str = Field(default="shared_experience", max_length=40)
    other_character_id: int | None = None
    importance: int = Field(default=50, ge=1, le=100)
    occurred_at: datetime | None = None
    context: dict | None = None


class AdminJobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    employer_location_id: int | None = None
    salary_per_shift: float = Field(default=0)
    schedule_template: dict | None = None


class AdminLocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    district_id: int
    kind: str = Field(default="shop", max_length=32)
    description: str = Field(default="", max_length=2000)
    is_public: bool = True


class AdminDistrictCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=0)


class JobsForCharacter(BaseModel):
    character_id: int
    job_id: int
    is_primary: bool = True
from datetime import datetime


from sqlmodel import Field, SQLModel


class StoryMilestone(SQLModel, table=True):
    __tablename__ = "story_milestones"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True, max_length=64)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)
    threshold: int = Field(default=5)


class MilestoneProgress(SQLModel, table=True):
    __tablename__ = "milestone_progress"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True, max_length=64)
    qualifying_count: int = Field(default=0)
    pending_opportunity: bool = Field(default=False)
    last_opportunity_at: datetime | None = Field(default=None)

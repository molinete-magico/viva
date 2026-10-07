from pydantic import BaseModel

from app.models import District, Location


class DistrictOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str


class LocationOut(BaseModel):
    id: int
    name: str
    slug: str
    district_id: int
    district_name: str
    kind: str
    description: str
    opening_hours: dict | None = None
    activities: list = []


class SimulationAdvanceRequest(BaseModel):
    minutes: int


class SimulationLogOut(BaseModel):
    id: int
    ran_at: str
    kind: str
    elapsed_minutes: int
    summary: str


def district_out(district: District) -> DistrictOut:
    return DistrictOut(
        id=district.id,
        name=district.name,
        slug=district.slug,
        description=district.description,
    )


def location_out(location: Location, district_name: str) -> LocationOut:
    return LocationOut(
        id=location.id,
        name=location.name,
        slug=location.slug,
        district_id=location.district_id,
        district_name=district_name,
        kind=location.kind,
        description=location.description,
        opening_hours=location.opening_hours,
        activities=list(location.activities or []),
    )

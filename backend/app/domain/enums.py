from enum import StrEnum


class PostKind(StrEnum):
    POST = "post"
    EVENT = "event"
    NEWS = "news"
    SYSTEM = "system"


class NotificationType(StrEnum):
    NEW_MESSAGE = "NEW_MESSAGE"
    EVENT_INVITE = "EVENT_INVITE"
    EVENT_STARTING = "EVENT_STARTING"
    POST_LIKE = "POST_LIKE"
    POST_COMMENT = "POST_COMMENT"
    RELATIONSHIP_CHANGE = "RELATIONSHIP_CHANGE"
    MILESTONE = "MILESTONE"
    NPC_DM_INITIATIVE = "NPC_DM_INITIATIVE"
    EVENT_RESULT = "EVENT_RESULT"


class ConversationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    ENDED = "ENDED"


class EventStatus(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class EventSessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class ParticipantStatus(StrEnum):
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    JOINED = "JOINED"
    LEFT = "LEFT"
    ABSENT = "ABSENT"


class FutureHookStatus(StrEnum):
    PENDING = "PENDING"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"


class FutureHookSource(StrEnum):
    EVENT = "event"
    DM = "dm"


class FutureHookKind(StrEnum):
    DM_MESSAGE = "dm_message"
    EVENT_INVITE = "event_invite"


class MemoryCategory(StrEnum):
    IMPORTANT = "IMPORTANT"
    NORMAL = "NORMAL"
    TEMPORARY = "TEMPORARY"


class MemoryKind(StrEnum):
    FIRST_MEETING = "first_meeting"
    PROMISE = "promise"
    FAVOR = "favor"
    ARGUMENT = "argument"
    DATE = "date"
    DISCOVERED_PREFERENCE = "discovered_preference"
    SHARED_EXPERIENCE = "shared_experience"
    SECRET = "secret"


class LocationKind(StrEnum):
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    SHOP = "shop"
    STREET = "street"
    PARK = "park"
    WORK = "work"
    HOME = "home"
    ARCADE = "arcade"


class PhotoSource(StrEnum):
    SEED = "seed"
    MANUAL = "manual"
    UPLOAD = "upload"


class SimulationKind(StrEnum):
    BOOTSTRAP = "bootstrap"
    CATCHUP = "catchup"
    MANUAL = "manual"
    ROUTINE = "routine"


class RelationshipDimension(StrEnum):
    FAMILIARITY = "familiarity"
    FRIENDSHIP = "friendship"
    TRUST = "trust"
    ROMANCE = "romance"
    RESPECT = "respect"
    TENSION = "tension"

from datetime import datetime

from pydantic import BaseModel, ConfigDict, NonNegativeInt, StrictStr, field_validator


def _validate_not_blank(value: str) -> str:
    if value.strip() == "":
        raise ValueError("must not be blank")

    return value


def _validate_rfc3339(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("must be RFC3339") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("must include timezone")

    return value


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class RegisterUserRequest(ApiModel):
    full_name: StrictStr
    username: StrictStr
    password: StrictStr

    @field_validator("full_name", "username", "password")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        return _validate_not_blank(value)


class LoginRequest(ApiModel):
    username: StrictStr
    password: StrictStr

    @field_validator("username", "password")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        return _validate_not_blank(value)


class CreateEventRequest(ApiModel):
    title: StrictStr
    address: StrictStr
    started_at: StrictStr
    finished_at: StrictStr
    description: StrictStr

    @field_validator("title", "address", "description")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        return _validate_not_blank(value)

    @field_validator("started_at", "finished_at")
    @classmethod
    def validate_rfc3339(cls, value: str) -> str:
        return _validate_rfc3339(_validate_not_blank(value))


class ListEventsQuery(ApiModel):
    title: str = ""
    limit: NonNegativeInt | None = None
    offset: NonNegativeInt = 0


class EventLocationResponse(ApiModel):
    address: str
    city: str | None = None


class EventReactionsResponse(ApiModel):
    likes: int
    dislikes: int


class EventReviewsResponse(ApiModel):
    count: int
    rating: float


class EventResponse(ApiModel):
    id: str
    title: str
    description: str
    location: EventLocationResponse
    created_at: str
    created_by: str
    started_at: str
    finished_at: str
    category: str | None = None
    price: int | None = None
    reactions: EventReactionsResponse | None = None
    reviews: EventReviewsResponse | None = None


class EventCreatedResponse(ApiModel):
    id: str


class EventListResponse(ApiModel):
    events: list[EventResponse]
    count: int


class UserResponse(ApiModel):
    id: str
    full_name: str
    username: str


class UserListResponse(ApiModel):
    users: list[UserResponse]
    count: int

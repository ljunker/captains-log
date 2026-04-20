from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.tags import normalize_tag_name, normalize_tag_names
from app.timezone import assume_utc, input_datetime_to_utc


class EntryBase(BaseModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be blank")
        return stripped

    @field_validator("tags", mode="before")
    @classmethod
    def default_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Tags must be a list")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return normalize_tag_names(value)


class EntryCreate(EntryBase):
    created_at: datetime | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def default_created_at(cls, value: object) -> datetime | None:
        if value in {None, ""}:
            return None
        return value

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return input_datetime_to_utc(value)


class EntryUpdate(EntryBase):
    pass


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    original_filename: str
    mime_type: str
    file_size: int
    created_at: datetime
    thumbnail_url: str | None = None
    file_url: str

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        return assume_utc(value).isoformat()


class EntryRead(EntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentRead] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def serialize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                if isinstance(item, str):
                    normalized.append(normalize_tag_name(item))
                    continue
                tag_name = getattr(item, "name", None)
                if isinstance(tag_name, str):
                    normalized.append(normalize_tag_name(tag_name))
            return normalized
        raise ValueError("Tags must be a list")

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return assume_utc(value).isoformat()


class EntryListResponse(BaseModel):
    day: date
    previous_day: date | None
    next_day: date | None
    active_tag: str | None
    active_search: str | None
    available_tags: list[str]
    entries: list[EntryRead]


class EntrySearchResult(BaseModel):
    day: date
    entry: EntryRead


class EntrySearchResponse(BaseModel):
    query: str
    results: list[EntrySearchResult]

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntryBase(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be blank")
        return stripped


class EntryCreate(EntryBase):
    pass


class EntryUpdate(EntryBase):
    pass


class EntryRead(EntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class EntryListResponse(BaseModel):
    day: date
    previous_day: date | None
    next_day: date | None
    entries: list[EntryRead]

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageParams(BaseModel):
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class PatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    non_nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        nulls = sorted(
            name
            for name in self.model_fields_set & self.non_nullable_fields
            if getattr(self, name) is None
        )
        if nulls:
            raise ValueError(f"Fields cannot be null: {', '.join(nulls)}")
        return self

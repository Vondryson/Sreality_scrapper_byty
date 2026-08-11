"""Contracts for private owner-managed listing state."""

from __future__ import annotations

from pydantic import Field, model_validator

from sreality_tracker.api.contracts import ApiModel


class UserListingUpdate(ApiModel):
    is_favorite: bool | None = None
    private_note: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def validate_patch(self) -> UserListingUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        if "is_favorite" in self.model_fields_set and self.is_favorite is None:
            raise ValueError("is_favorite cannot be null")
        return self


class UserListingResponse(ApiModel):
    listing_id: int
    is_favorite: bool
    private_note: str | None
    archived_images: int
    failed_images: int

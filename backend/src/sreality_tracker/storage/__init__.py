"""Raw payload and image storage adapters."""

from sreality_tracker.storage.raw import (
    GcsRawStorage,
    LocalRawStorage,
    RawObjectRef,
    RawStorage,
)

__all__ = ["GcsRawStorage", "LocalRawStorage", "RawObjectRef", "RawStorage"]

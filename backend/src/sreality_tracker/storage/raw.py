"""Idempotent compressed raw-payload storage adapters."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast
from uuid import UUID

from google.api_core.exceptions import GoogleAPICallError, NotFound, PreconditionFailed
from google.cloud import storage as google_storage  # type: ignore[import-untyped]

DEFAULT_PREFIX = "raw"


class RawStorageError(RuntimeError):
    """Base error raised by raw storage adapters."""


class RawStorageConflictError(RawStorageError):
    """Raised when an immutable object key already contains different bytes."""


class RawStorageDataError(RawStorageError):
    """Raised when payload serialization or stored data is invalid."""


@dataclass(frozen=True, slots=True)
class RawObjectRef:
    key: str
    sha256: str
    uncompressed_size: int
    compressed_size: int


class RawStorage(Protocol):
    """Unified raw-payload interface used by the pipeline."""

    def store_json(
        self, *, run_id: UUID, sreality_id: int, payload: Mapping[str, Any]
    ) -> RawObjectRef: ...

    def load_json(self, key: str) -> dict[str, Any]: ...


class _BlobLike(Protocol):
    metadata: dict[str, str] | None

    def upload_from_string(
        self,
        data: bytes,
        *,
        content_type: str,
        if_generation_match: int,
        checksum: str,
    ) -> None: ...

    def download_as_bytes(self, *, checksum: str = "auto") -> bytes: ...


class _BucketLike(Protocol):
    def blob(self, blob_name: str) -> _BlobLike: ...


@dataclass(frozen=True, slots=True)
class _SerializedPayload:
    raw: bytes
    compressed: bytes
    sha256: str

    def reference(self, key: str) -> RawObjectRef:
        return RawObjectRef(
            key=key,
            sha256=self.sha256,
            uncompressed_size=len(self.raw),
            compressed_size=len(self.compressed),
        )


def raw_object_key(*, run_id: UUID, sreality_id: int, prefix: str = DEFAULT_PREFIX) -> str:
    """Build the canonical run/listing object key."""
    normalized_prefix = _validate_prefix(prefix)
    if sreality_id <= 0:
        raise ValueError("sreality_id must be positive")
    return f"{normalized_prefix}/runs/{run_id}/listings/{sreality_id}.json.gz"


def serialize_payload(payload: Mapping[str, Any]) -> _SerializedPayload:
    """Serialize JSON deterministically and gzip it with a stable header."""
    try:
        raw = json.dumps(
            dict(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RawStorageDataError("payload is not valid finite JSON") from error
    return _SerializedPayload(
        raw=raw,
        compressed=gzip.compress(raw, compresslevel=6, mtime=0),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def deserialize_payload(compressed: bytes) -> dict[str, Any]:
    """Decompress a stored object and require a JSON object root."""
    try:
        raw = gzip.decompress(compressed)
        value = json.loads(raw.decode("utf-8"))
    except (gzip.BadGzipFile, EOFError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RawStorageDataError("stored object is not valid gzip JSON") from error
    if not isinstance(value, dict):
        raise RawStorageDataError("stored JSON root must be an object")
    return value


class LocalRawStorage:
    """Store immutable raw objects below an explicit local root directory."""

    def __init__(self, root: Path, *, prefix: str = DEFAULT_PREFIX) -> None:
        self._root = root.resolve()
        self._prefix = _validate_prefix(prefix)

    def store_json(
        self, *, run_id: UUID, sreality_id: int, payload: Mapping[str, Any]
    ) -> RawObjectRef:
        key = raw_object_key(run_id=run_id, sreality_id=sreality_id, prefix=self._prefix)
        serialized = serialize_payload(payload)
        target = self._safe_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            return self._verify_existing(target.read_bytes(), serialized, key)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=".raw-", suffix=".tmp", delete=False
            ) as temporary:
                temporary.write(serialized.compressed)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.link(temporary_path, target)
            except FileExistsError:
                return self._verify_existing(target.read_bytes(), serialized, key)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return serialized.reference(key)

    def load_json(self, key: str) -> dict[str, Any]:
        target = self._safe_path(key)
        try:
            compressed = target.read_bytes()
        except FileNotFoundError as error:
            raise RawStorageError(f"raw object does not exist: {key}") from error
        return deserialize_payload(compressed)

    def _safe_path(self, key: str) -> Path:
        _validate_object_key(key, self._prefix)
        target = (self._root / Path(*PurePosixPath(key).parts)).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("raw object key escapes the storage root")
        return target

    @staticmethod
    def _verify_existing(existing: bytes, serialized: _SerializedPayload, key: str) -> RawObjectRef:
        if existing != serialized.compressed:
            raise RawStorageConflictError(
                f"raw object key already contains different content: {key}"
            )
        return serialized.reference(key)


class GcsRawStorage:
    """Store immutable raw objects in a private Google Cloud Storage bucket."""

    def __init__(self, bucket: _BucketLike, *, prefix: str = DEFAULT_PREFIX) -> None:
        self._bucket = bucket
        self._prefix = _validate_prefix(prefix)

    @classmethod
    def from_bucket_name(
        cls, bucket_name: str, *, project: str | None = None, prefix: str = DEFAULT_PREFIX
    ) -> GcsRawStorage:
        if not bucket_name.strip():
            raise ValueError("bucket_name must not be empty")
        client = google_storage.Client(project=project)
        bucket = cast(_BucketLike, client.bucket(bucket_name))
        return cls(bucket, prefix=prefix)

    def store_json(
        self, *, run_id: UUID, sreality_id: int, payload: Mapping[str, Any]
    ) -> RawObjectRef:
        key = raw_object_key(run_id=run_id, sreality_id=sreality_id, prefix=self._prefix)
        serialized = serialize_payload(payload)
        blob = self._bucket.blob(key)
        blob.metadata = {
            "sha256": serialized.sha256,
            "uncompressed-size": str(len(serialized.raw)),
        }
        try:
            blob.upload_from_string(
                serialized.compressed,
                content_type="application/gzip",
                if_generation_match=0,
                checksum="crc32c",
            )
        except PreconditionFailed:
            existing = blob.download_as_bytes(checksum="auto")
            if existing != serialized.compressed:
                raise RawStorageConflictError(
                    f"raw object key already contains different content: {key}"
                ) from None
        return serialized.reference(key)

    def load_json(self, key: str) -> dict[str, Any]:
        _validate_object_key(key, self._prefix)
        try:
            compressed = self._bucket.blob(key).download_as_bytes(checksum="auto")
        except NotFound as error:
            raise RawStorageError(f"raw object does not exist: {key}") from error
        except GoogleAPICallError as error:
            raise RawStorageError(f"failed to load raw object: {key}") from error
        return deserialize_payload(compressed)


def _validate_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("raw storage prefix must be a relative object prefix")
    return path.as_posix()


def _validate_object_key(key: str, prefix: str) -> None:
    path = PurePosixPath(key)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("raw object key must be relative and cannot contain traversal")
    if not key.startswith(f"{prefix}/runs/") or not key.endswith(".json.gz"):
        raise ValueError("raw object key does not match the configured prefix and format")

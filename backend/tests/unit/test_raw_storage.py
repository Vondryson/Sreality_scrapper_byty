from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from google.api_core.exceptions import NotFound, PreconditionFailed

from sreality_tracker.storage.raw import (
    GcsRawStorage,
    LocalRawStorage,
    RawStorageConflictError,
    RawStorageDataError,
    RawStorageError,
    raw_object_key,
    serialize_payload,
)

RUN_ID = UUID("11111111-2222-3333-4444-555555555555")
PAYLOAD: dict[str, Any] = {
    "name": "Chata v Česku",
    "priceCzk": 2_500_000,
    "params": {"usableArea": 80, "future": [1, 2, 3]},
}


class FakeBlob:
    def __init__(self, name: str, objects: dict[str, bytes]) -> None:
        self.name = name
        self.objects = objects
        self.metadata: dict[str, str] | None = None
        self.upload_calls = 0
        self.last_upload_options: dict[str, object] = {}

    def upload_from_string(
        self,
        data: bytes,
        *,
        content_type: str,
        if_generation_match: int,
        checksum: str,
    ) -> None:
        self.upload_calls += 1
        self.last_upload_options = {
            "content_type": content_type,
            "if_generation_match": if_generation_match,
            "checksum": checksum,
        }
        if self.name in self.objects:
            raise PreconditionFailed("object exists")  # type: ignore[no-untyped-call]
        self.objects[self.name] = data

    def download_as_bytes(self, *, checksum: str = "auto") -> bytes:
        if self.name not in self.objects:
            raise NotFound("object does not exist")  # type: ignore[no-untyped-call]
        assert checksum == "auto"
        return self.objects[self.name]


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, blob_name: str) -> FakeBlob:
        blob = FakeBlob(blob_name, self.objects)
        self.blobs[blob_name] = blob
        return blob


def test_serialization_is_deterministic_compressed_utf8_json() -> None:
    first = serialize_payload(PAYLOAD)
    second = serialize_payload(dict(reversed(PAYLOAD.items())))

    assert first.raw == second.raw
    assert first.compressed == second.compressed
    assert first.sha256 == second.sha256
    assert gzip.decompress(first.compressed) == first.raw
    assert "Česku" in first.raw.decode("utf-8")


def test_local_storage_round_trip_and_idempotent_noop(tmp_path: Path) -> None:
    storage = LocalRawStorage(tmp_path)

    first = storage.store_json(run_id=RUN_ID, sreality_id=123456, payload=PAYLOAD)
    target = tmp_path / Path(*first.key.split("/"))
    first_stat = target.stat()
    second = storage.store_json(run_id=RUN_ID, sreality_id=123456, payload=PAYLOAD)

    assert first == second
    assert target.stat().st_mtime_ns == first_stat.st_mtime_ns
    assert storage.load_json(first.key) == PAYLOAD
    assert first.key == ("raw/runs/11111111-2222-3333-4444-555555555555/listings/123456.json.gz")
    assert first.compressed_size == target.stat().st_size
    assert first.compressed_size > 0


def test_local_storage_rejects_conflict_and_invalid_keys(tmp_path: Path) -> None:
    storage = LocalRawStorage(tmp_path)
    reference = storage.store_json(run_id=RUN_ID, sreality_id=123, payload=PAYLOAD)

    with pytest.raises(RawStorageConflictError, match="different content"):
        storage.store_json(run_id=RUN_ID, sreality_id=123, payload={"changed": True})
    with pytest.raises(ValueError, match="relative"):
        storage.load_json("../outside.json.gz")
    with pytest.raises(RawStorageError, match="does not exist"):
        storage.load_json(raw_object_key(run_id=RUN_ID, sreality_id=999))

    target = tmp_path / Path(*reference.key.split("/"))
    target.write_bytes(b"not-gzip")
    with pytest.raises(RawStorageDataError, match="gzip JSON"):
        storage.load_json(reference.key)


def test_payload_must_be_finite_json() -> None:
    with pytest.raises(RawStorageDataError, match="finite JSON"):
        serialize_payload({"invalid": float("nan")})
    with pytest.raises(RawStorageDataError, match="finite JSON"):
        serialize_payload({"invalid": object()})


def test_gcs_storage_uses_create_only_upload_and_round_trip() -> None:
    bucket = FakeBucket()
    storage = GcsRawStorage(bucket)

    first = storage.store_json(run_id=RUN_ID, sreality_id=123, payload=PAYLOAD)
    uploaded_blob = bucket.blobs[first.key]
    second = storage.store_json(run_id=RUN_ID, sreality_id=123, payload=PAYLOAD)

    assert first == second
    assert storage.load_json(first.key) == PAYLOAD
    assert uploaded_blob.last_upload_options == {
        "content_type": "application/gzip",
        "if_generation_match": 0,
        "checksum": "crc32c",
    }
    assert uploaded_blob.metadata == {
        "sha256": first.sha256,
        "uncompressed-size": str(first.uncompressed_size),
    }


def test_gcs_storage_rejects_existing_different_content() -> None:
    bucket = FakeBucket()
    storage = GcsRawStorage(bucket)
    storage.store_json(run_id=RUN_ID, sreality_id=123, payload=PAYLOAD)

    with pytest.raises(RawStorageConflictError, match="different content"):
        storage.store_json(run_id=RUN_ID, sreality_id=123, payload={"changed": True})


def test_gcs_storage_maps_missing_object_error() -> None:
    storage = GcsRawStorage(FakeBucket())
    key = raw_object_key(run_id=RUN_ID, sreality_id=123)

    with pytest.raises(RawStorageError, match="does not exist"):
        storage.load_json(key)

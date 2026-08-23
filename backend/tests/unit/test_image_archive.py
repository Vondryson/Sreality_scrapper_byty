from pathlib import Path

import pytest
from google.api_core.exceptions import NotFound, PreconditionFailed

from sreality_tracker.storage.images import (
    FetchedImage,
    GcsImageArchiveStorage,
    HttpxImageFetcher,
    ImageArchiveConflictError,
    ImageArchiveError,
    LocalImageArchiveStorage,
    image_archive_key,
)


class FakeBlob:
    def __init__(self, name: str, objects: dict[str, bytes]) -> None:
        self.name = name
        self.objects = objects
        self.last_upload_options: dict[str, object] = {}

    def upload_from_string(
        self,
        data: bytes,
        *,
        content_type: str,
        if_generation_match: int,
        checksum: str,
    ) -> None:
        self.last_upload_options = {
            "content_type": content_type,
            "if_generation_match": if_generation_match,
            "checksum": checksum,
        }
        if self.name in self.objects:
            raise PreconditionFailed("object exists")  # type: ignore[no-untyped-call]
        self.objects[self.name] = data

    def download_as_bytes(self, *, checksum: str = "auto") -> bytes:
        assert checksum == "auto"
        if self.name not in self.objects:
            raise NotFound("object does not exist")  # type: ignore[no-untyped-call]
        return self.objects[self.name]


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, blob_name: str) -> FakeBlob:
        blob = FakeBlob(blob_name, self.objects)
        self.blobs[blob_name] = blob
        return blob


def test_local_image_archive_is_immutable_and_idempotent(tmp_path: Path) -> None:
    storage = LocalImageArchiveStorage(tmp_path)
    key = image_archive_key(listing_id=42, source_fingerprint="a" * 64)
    image = FetchedImage(content=b"jpeg-content", content_type="image/jpeg")

    first = storage.store(key=key, image=image)
    repeated = storage.store(key=key, image=image)

    assert repeated == first
    assert (tmp_path / "favorite-images" / "42" / f"{'a' * 64}.bin").read_bytes() == b"jpeg-content"
    with pytest.raises(ImageArchiveConflictError):
        storage.store(
            key=key,
            image=FetchedImage(content=b"different", content_type="image/jpeg"),
        )


@pytest.mark.parametrize(
    "source_url",
    [
        "http://d18-a.sdn.cz/image.jpg",
        "https://example.com/image.jpg",
        "https://sdn.cz.evil.invalid/image.jpg",
        "file:///etc/passwd",
    ],
)
def test_http_fetcher_rejects_untrusted_sources_before_network(source_url: str) -> None:
    with pytest.raises(ImageArchiveError):
        HttpxImageFetcher().fetch(source_url)


def test_image_archive_key_rejects_invalid_identity() -> None:
    with pytest.raises(ValueError):
        image_archive_key(listing_id=0, source_fingerprint="a" * 64)
    with pytest.raises(ValueError):
        image_archive_key(listing_id=1, source_fingerprint="../escape")


def test_local_archive_loads_only_recognized_bitmap_content(tmp_path: Path) -> None:
    storage = LocalImageArchiveStorage(tmp_path)
    valid_key = image_archive_key(listing_id=1, source_fingerprint="b" * 64)
    invalid_key = image_archive_key(listing_id=1, source_fingerprint="c" * 64)
    storage.store(
        key=valid_key,
        image=FetchedImage(content=b"\xff\xd8\xffjpeg-data", content_type="image/jpeg"),
    )
    storage.store(
        key=invalid_key,
        image=FetchedImage(content=b"<svg onload='alert(1)'>", content_type="image/svg+xml"),
    )

    loaded = storage.load(key=valid_key)
    assert loaded.content_type == "image/jpeg"
    assert loaded.content.startswith(b"\xff\xd8\xff")
    with pytest.raises(ImageArchiveError, match="invalid format"):
        storage.load(key=invalid_key)


def test_gcs_image_archive_is_create_only_idempotent_and_validates_content() -> None:
    bucket = FakeBucket()
    storage = GcsImageArchiveStorage(bucket)
    key = image_archive_key(listing_id=42, source_fingerprint="d" * 64)
    image = FetchedImage(content=b"\xff\xd8\xffjpeg-data", content_type="image/jpeg")

    first = storage.store(key=key, image=image)
    uploaded_blob = bucket.blobs[key]
    repeated = storage.store(key=key, image=image)

    assert repeated == first
    assert storage.load(key=key).content == image.content
    assert uploaded_blob.last_upload_options == {
        "content_type": "image/jpeg",
        "if_generation_match": 0,
        "checksum": "crc32c",
    }
    with pytest.raises(ImageArchiveConflictError, match="different content"):
        storage.store(
            key=key,
            image=FetchedImage(content=b"different", content_type="image/jpeg"),
        )


def test_gcs_image_archive_maps_missing_object_and_rejects_invalid_key() -> None:
    storage = GcsImageArchiveStorage(FakeBucket())
    key = image_archive_key(listing_id=42, source_fingerprint="e" * 64)

    with pytest.raises(ImageArchiveError, match="unavailable"):
        storage.load(key=key)
    with pytest.raises(ValueError, match="invalid image archive key"):
        storage.load(key="../favorite-images/escape.bin")

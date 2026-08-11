from pathlib import Path

import pytest

from sreality_tracker.storage.images import (
    FetchedImage,
    HttpxImageFetcher,
    ImageArchiveConflictError,
    ImageArchiveError,
    LocalImageArchiveStorage,
    image_archive_key,
)


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

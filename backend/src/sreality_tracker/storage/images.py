"""Idempotent private storage and source fetching for favorite listing images."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import urlparse

import httpx

IMAGE_PREFIX = "favorite-images"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_HOST_SUFFIXES = (".sdn.cz",)


class ImageArchiveError(RuntimeError):
    """Safe base error for image retrieval and persistence failures."""


class ImageArchiveConflictError(ImageArchiveError):
    """An immutable archive key already contains different bytes."""


@dataclass(frozen=True, slots=True)
class FetchedImage:
    content: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class ArchivedImage:
    key: str
    sha256: str
    size: int


class ImageFetcher(Protocol):
    def fetch(self, source_url: str) -> FetchedImage: ...


class ImageArchiveStorage(Protocol):
    def store(self, *, key: str, image: FetchedImage) -> ArchivedImage: ...


class HttpxImageFetcher:
    """Fetch a bounded HTTPS image without exposing response details in errors."""

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch(self, source_url: str) -> FetchedImage:
        parsed = urlparse(source_url)
        if not _is_allowed_source(parsed.scheme, parsed.hostname):
            raise ImageArchiveError("image source must be an absolute HTTPS URL")
        try:
            with (
                httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client,
                client.stream("GET", source_url) as response,
            ):
                response.raise_for_status()
                final_url = urlparse(str(response.url))
                if not _is_allowed_source(final_url.scheme, final_url.hostname):
                    raise ImageArchiveError("image redirect target is not allowed")
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                if not content_type.startswith("image/"):
                    raise ImageArchiveError("image response has an invalid content type")
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise ImageArchiveError("image exceeds the archive size limit")
                    chunks.append(chunk)
        except (httpx.HTTPError, OSError) as error:
            raise ImageArchiveError("image download failed") from error
        return FetchedImage(content=b"".join(chunks), content_type=content_type)


class LocalImageArchiveStorage:
    """Create immutable private image objects below an explicit local root."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def store(self, *, key: str, image: FetchedImage) -> ArchivedImage:
        target = self._safe_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(image.content).hexdigest()
        result = ArchivedImage(key=key, sha256=digest, size=len(image.content))
        if target.exists():
            if target.read_bytes() != image.content:
                raise ImageArchiveConflictError("archive key contains different content")
            return result

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=".image-", suffix=".tmp", delete=False
            ) as temporary:
                temporary.write(image.content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.link(temporary_path, target)
            except FileExistsError:
                if target.read_bytes() != image.content:
                    raise ImageArchiveConflictError(
                        "archive key contains different content"
                    ) from None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return result

    def _safe_path(self, key: str) -> Path:
        path = PurePosixPath(key)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not key.startswith(f"{IMAGE_PREFIX}/")
        ):
            raise ValueError("invalid image archive key")
        target = (self._root / Path(*path.parts)).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("image archive key escapes the storage root")
        return target


def image_archive_key(*, listing_id: int, source_fingerprint: str) -> str:
    if listing_id <= 0:
        raise ValueError("listing_id must be positive")
    if len(source_fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in source_fingerprint
    ):
        raise ValueError("source_fingerprint must be a lowercase SHA-256 digest")
    return f"{IMAGE_PREFIX}/{listing_id}/{source_fingerprint}.bin"


def _is_allowed_source(scheme: str, hostname: str | None) -> bool:
    if scheme != "https" or hostname is None:
        return False
    normalized = hostname.rstrip(".").lower()
    return any(normalized.endswith(suffix) for suffix in ALLOWED_IMAGE_HOST_SUFFIXES)

"""Private prescription PDF storage adapters for Phase 13.

Local development uses a private filesystem directory. Production uses a
private Vercel Blob store so documents survive function restarts and
deployments. Storage keys remain backend-only and are never returned to a
browser.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from vercel.blob import BlobClient
from vercel.blob.errors import BlobNotFoundError

from app.core.config import BACKEND_DIRECTORY, get_settings


class PrescriptionStorage(ABC):
    """Strategy interface for persisting prescription PDF binaries."""

    @abstractmethod
    def save(self, prescription_id, file_name: str, payload: bytes) -> str:
        """Persist ``payload`` and return an opaque storage key."""

    @abstractmethod
    def load(self, storage_key: str) -> bytes:
        """Return the bytes previously stored under ``storage_key``."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove the bytes stored under ``storage_key`` (idempotent)."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return whether ``storage_key`` currently points at a file."""


class LocalPrescriptionStorage(PrescriptionStorage):
    """Filesystem-backed implementation for development and tests."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def save(
        self, prescription_id, file_name: str, payload: bytes
    ) -> str:
        prescription_dir = self._root / str(prescription_id)
        prescription_dir.mkdir(parents=True, exist_ok=True)
        # ``os.path.join`` mangles a leading slash in ``file_name`` away
        # on Windows; resolve a relative path manually.
        target = prescription_dir / Path(file_name).name
        target.write_bytes(payload)
        return str(target.relative_to(self._root))

    def _target_for_key(self, storage_key: str) -> Path:
        target = (self._root / storage_key).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as error:
            raise FileNotFoundError(
                "Invalid prescription storage key."
            ) from error
        return target

    def load(self, storage_key: str) -> bytes:
        return self._target_for_key(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        target = self._target_for_key(storage_key)
        try:
            target.unlink()
        except FileNotFoundError:
            pass

    def exists(self, storage_key: str) -> bool:
        return self._target_for_key(storage_key).is_file()


class VercelBlobPrescriptionStorage(PrescriptionStorage):
    """Private, durable production storage backed by Vercel Blob."""

    def __init__(self, token: str, *, client: Any | None = None) -> None:
        normalized_token = token.strip()
        if not normalized_token:
            raise RuntimeError(
                "BLOB_READ_WRITE_TOKEN is required for vercel_blob storage."
            )
        self._client = client or BlobClient(token=normalized_token)

    def save(
        self, prescription_id, file_name: str, payload: bytes
    ) -> str:
        pathname = (
            f"prescriptions/{prescription_id}/{Path(file_name).name}"
        )
        uploaded = self._client.put(
            pathname,
            payload,
            access="private",
            content_type="application/pdf",
            overwrite=False,
            cache_control_max_age=60,
        )
        return uploaded.pathname

    def load(self, storage_key: str) -> bytes:
        result = self._client.get(
            storage_key,
            access="private",
            use_cache=True,
        )
        if result is None or result.status_code != 200:
            raise FileNotFoundError(storage_key)
        return bytes(result)

    def delete(self, storage_key: str) -> None:
        self._client.delete(storage_key)

    def exists(self, storage_key: str) -> bool:
        try:
            self._client.head(storage_key)
        except BlobNotFoundError:
            return False
        return True


def _resolve_storage_root() -> Path:
    settings = get_settings()
    raw = settings.prescription_storage_path.strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (BACKEND_DIRECTORY / ".prescription_storage").resolve()


_storage_singleton: PrescriptionStorage | None = None


def get_prescription_storage() -> PrescriptionStorage:
    """Module-level accessor used by services, routes, and tests."""

    global _storage_singleton
    if _storage_singleton is None:
        settings = get_settings()
        backend = settings.prescription_storage_backend
        if backend == "local":
            _storage_singleton = LocalPrescriptionStorage(
                _resolve_storage_root()
            )
        elif backend == "vercel_blob":
            _storage_singleton = VercelBlobPrescriptionStorage(
                settings.blob_read_write_token
            )
        else:  # pragma: no cover - Settings rejects unsupported literals.
            raise RuntimeError(
                f"Unsupported prescription storage backend: {backend!r}"
            )
    return _storage_singleton


def reset_prescription_storage_for_tests(
    storage: PrescriptionStorage | None,
) -> None:
    """Test hook: swap or clear the module singleton storage backend."""

    global _storage_singleton
    _storage_singleton = storage
    if storage is None:
        # Force the next call to ``get_prescription_storage`` to
        # rebuild from the test's monkey-patched settings.
        from app.core.config import get_settings

        get_settings.cache_clear()


__all__ = [
    "LocalPrescriptionStorage",
    "PrescriptionStorage",
    "VercelBlobPrescriptionStorage",
    "get_prescription_storage",
    "reset_prescription_storage_for_tests",
]

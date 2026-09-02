"""Phase 13 private prescription PDF storage abstraction.

V6 section 28 places the rendered PDF in private object storage. Only
Phase 13 ships a local filesystem backend; the ``PrescriptionStorage``
protocol leaves room for an object-storage adapter in production
without changing routes or services.

Keys are opaque to callers; the local backend derives them from the
prescription id so the directory tree stays predictable and easy to
wipe in development.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

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

    def load(self, storage_key: str) -> bytes:
        return (self._root / storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        target = self._root / storage_key
        try:
            target.unlink()
        except FileNotFoundError:
            pass

    def exists(self, storage_key: str) -> bool:
        return (self._root / storage_key).is_file()


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
        backend = get_settings().prescription_storage_backend
        if backend != "local":
            raise RuntimeError(
                f"Unsupported prescription storage backend: {backend!r}"
            )
        _storage_singleton = LocalPrescriptionStorage(_resolve_storage_root())
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
    "get_prescription_storage",
    "reset_prescription_storage_for_tests",
]
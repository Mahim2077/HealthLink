from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from vercel.blob.errors import BlobNotFoundError

from app.prescriptions.storage import (
    LocalPrescriptionStorage,
    VercelBlobPrescriptionStorage,
)


@dataclass
class _Uploaded:
    pathname: str


@dataclass
class _Downloaded:
    content: bytes
    status_code: int = 200

    def __bytes__(self) -> bytes:
        return self.content


class _FakeBlobClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.last_put: dict | None = None

    def put(self, pathname: str, payload: bytes, **options):
        self.last_put = {"pathname": pathname, **options}
        self.objects[pathname] = payload
        return _Uploaded(pathname=pathname)

    def get(self, pathname: str, **options):
        del options
        payload = self.objects.get(pathname)
        return _Downloaded(payload) if payload is not None else None

    def head(self, pathname: str):
        if pathname not in self.objects:
            raise BlobNotFoundError()
        return object()

    def delete(self, pathname: str) -> None:
        self.objects.pop(pathname, None)


def test_vercel_blob_adapter_keeps_prescriptions_private() -> None:
    fake = _FakeBlobClient()
    storage = VercelBlobPrescriptionStorage("test-token", client=fake)
    prescription_id = uuid.uuid4()

    key = storage.save(prescription_id, "version.pdf", b"%PDF-test")

    assert key == f"prescriptions/{prescription_id}/version.pdf"
    assert fake.last_put == {
        "pathname": key,
        "access": "private",
        "content_type": "application/pdf",
        "overwrite": False,
        "cache_control_max_age": 60,
    }
    assert storage.exists(key) is True
    assert storage.load(key) == b"%PDF-test"
    storage.delete(key)
    assert storage.exists(key) is False


def test_vercel_blob_adapter_requires_token() -> None:
    with pytest.raises(RuntimeError, match="BLOB_READ_WRITE_TOKEN"):
        VercelBlobPrescriptionStorage("   ")


def test_local_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalPrescriptionStorage(tmp_path)
    with pytest.raises(FileNotFoundError, match="Invalid prescription"):
        storage.load("../outside.pdf")

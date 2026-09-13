"""Where uploaded documents live.

The filesystem backend is what a clone without MinIO gets, so it is tested
directly. The S3 backend is tested through a stub client rather than a
container: what matters here is the key shape, the bucket isolation and the
read fallback, none of which need a real server to get wrong.
"""

from __future__ import annotations

import pytest
from botocore.exceptions import ClientError

from app.core.storage import LocalDocumentStorage, object_key

# --------------------------------------------------------------------- keys

def test_a_key_is_type_and_name() -> None:
    assert object_key("rne_extract", "page.png") == "rne_extract/page.png"


@pytest.mark.parametrize(
    ("document_type", "name"),
    [
        ("../../etc", "passwd"),
        ("rne_extract", "../../../etc/passwd"),
        ("/etc", "passwd"),
        ("rne_extract", "/etc/passwd"),
    ],
)
def test_a_key_cannot_climb_out_of_its_prefix(document_type: str, name: str) -> None:
    """Both segments arrive from a URL in some paths."""
    key = object_key(document_type, name)
    assert ".." not in key
    assert not key.startswith("/")
    assert key.count("/") == 1


@pytest.mark.parametrize(("document_type", "name"), [("", "a.png"), ("rne_extract", "")])
def test_an_empty_segment_is_refused(document_type: str, name: str) -> None:
    with pytest.raises(ValueError):
        object_key(document_type, name)


# --------------------------------------------------------------- filesystem

def test_local_storage_round_trips(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path)
    assert storage.exists("rne_extract/a.png") is False

    storage.put("rne_extract/a.png", b"bytes", "image/png")
    assert storage.exists("rne_extract/a.png") is True
    assert storage.get("rne_extract/a.png") == b"bytes"


def test_local_storage_returns_none_for_a_missing_object(tmp_path) -> None:
    assert LocalDocumentStorage(tmp_path).get("rne_extract/nope.png") is None


def test_local_storage_refuses_to_write_outside_its_root(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path / "uploads")
    with pytest.raises(ValueError):
        storage.put("../escaped.png", b"bytes", "image/png")


# ------------------------------------------------------------------- fallback

class _Stub:
    """Enough of the S3 client surface for the fallback path."""

    def __init__(self, stored: dict[str, bytes] | None = None, fail: bool = False):
        self.stored = stored or {}
        self.fail = fail
        self.created: list[str] = []

    def head_bucket(self, Bucket):
        if self.fail:
            raise _ClientError()

    def create_bucket(self, Bucket):
        self.created.append(Bucket)

    def put_object(self, Bucket, Key, Body, ContentType):
        self.stored[Key] = Body

    def get_object(self, Bucket, Key):
        if Key not in self.stored:
            raise _ClientError()
        return {"Body": _Body(self.stored[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.stored:
            raise _ClientError()


def _ClientError() -> ClientError:
    """The real botocore error, which is what the storage code catches."""
    return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


class _Body:
    def __init__(self, data: bytes):
        self.data = data

    def read(self) -> bytes:
        return self.data


def _s3(stub, fallback=None):
    from app.core import storage as module

    # Built without __init__ so no client is constructed and no bucket touched.
    instance = object.__new__(module.S3DocumentStorage)
    instance.bucket = "sahilli-documents"
    instance.fallback = fallback
    instance._client = stub
    return instance


def test_s3_reads_fall_back_to_the_filesystem(tmp_path) -> None:
    """A dossier filed before the bucket existed must keep opening.

    A migration that has to run before the application works again is a
    migration that will be forgotten.
    """
    local = LocalDocumentStorage(tmp_path)
    local.put("rne_extract/old.png", b"on disk", "image/png")

    storage = _s3(_Stub(), fallback=local)
    assert storage.get("rne_extract/old.png") == b"on disk"
    assert storage.exists("rne_extract/old.png") is True


def test_s3_prefers_the_bucket_when_the_object_is_there(tmp_path) -> None:
    local = LocalDocumentStorage(tmp_path)
    local.put("rne_extract/a.png", b"stale disk copy", "image/png")

    storage = _s3(_Stub({"rne_extract/a.png": b"bucket copy"}), fallback=local)
    assert storage.get("rne_extract/a.png") == b"bucket copy"


def test_s3_with_no_fallback_returns_none() -> None:
    assert _s3(_Stub()).get("rne_extract/a.png") is None


def test_unconfigured_storage_is_the_filesystem(tmp_path, monkeypatch) -> None:
    from app.core import storage as module

    monkeypatch.setattr(module.settings, "s3_endpoint_url", "")
    assert isinstance(module.build_storage(tmp_path), LocalDocumentStorage)


def test_an_unreachable_bucket_degrades_to_the_filesystem(tmp_path, monkeypatch) -> None:
    """Losing object storage must not stop the registry accepting filings."""
    from app.core import storage as module

    monkeypatch.setattr(module.settings, "s3_endpoint_url", "http://127.0.0.1:1")
    monkeypatch.setattr(module.settings, "s3_access_key", "x")
    monkeypatch.setattr(module.settings, "s3_secret_key", "x")

    def explode(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(module, "S3DocumentStorage", explode)
    assert isinstance(module.build_storage(tmp_path), LocalDocumentStorage)

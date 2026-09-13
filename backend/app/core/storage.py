"""Where uploaded documents live.

Documents were written to a directory beside the code. That is fine on one
laptop and wrong everywhere else: a second backend process cannot read what the
first one wrote, a container restart without a mounted volume loses a citizen's
identity papers, and nothing separates "the application" from "the evidence it
was given".

Object storage separates them. Sahilli talks S3 and is pointed at the MinIO
already running on this machine.

Two things are deliberate.

**The filesystem backend stays.** A clone with no MinIO still runs, and the
tests do not need a container to exercise upload handling. Storage is chosen by
configuration, not by an import.

**S3 reads fall back to the filesystem.** Dossiers filed before this existed
have their pages on disk, and a migration that must run before the application
works again is a migration that will be forgotten. An old dossier keeps opening;
a new one is written to the bucket.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


def object_key(document_type: str, stored_name: str) -> str:
    """The key a document is addressed by, identical in both backends.

    Both segments are reduced to a bare filename first: they reach us from a
    URL in some paths, and `..` in either one must not climb out of the
    prefix -- or, on the filesystem backend, out of the upload directory.
    """
    safe_type = Path(document_type).name
    safe_name = Path(stored_name).name
    if not safe_type or not safe_name:
        raise ValueError("A document key needs both a type and a name")
    return f"{safe_type}/{safe_name}"


class DocumentStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def exists(self, key: str) -> bool: ...


class LocalDocumentStorage:
    """Files under a directory. The original behaviour, kept honest."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path | None:
        root = self.root.resolve()
        candidate = (root / key).resolve()
        # The key is already sanitised, but this is the last gate before a
        # filesystem call and it costs nothing.
        return candidate if candidate.is_relative_to(root) else None

    def put(self, key: str, content: bytes, content_type: str) -> None:
        path = self._path(key)
        if path is None:
            raise ValueError(f"Refusing to write outside the upload directory: {key!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if path is None or not path.is_file():
            return None
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        path = self._path(key)
        return path is not None and path.is_file()


class S3DocumentStorage:
    """An S3-compatible bucket, with the filesystem as a read fallback."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        fallback: DocumentStorage | None = None,
    ) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.fallback = fallback
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            # Only ever creates its own bucket. Other projects share this MinIO
            # and their buckets are none of our business.
            self._client.create_bucket(Bucket=self.bucket)
            logger.info("Created document bucket %s", self.bucket)

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket, Key=key, Body=content, ContentType=content_type
        )

    def get(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError:
            # Filed before the bucket existed, or genuinely absent.
            return self.fallback.get(key) if self.fallback else None

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return bool(self.fallback and self.fallback.exists(key))


def build_storage(upload_dir: Path) -> DocumentStorage:
    """The configured backend, or the filesystem when none is configured."""
    local = LocalDocumentStorage(upload_dir)

    if not settings.s3_endpoint_url:
        return local

    try:
        return S3DocumentStorage(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            fallback=local,
        )
    except Exception as exc:  # noqa: BLE001
        # Losing object storage should degrade the deployment, not stop it
        # accepting filings. The warning is loud because the difference matters.
        logger.warning(
            "Object storage at %s is unavailable (%s); documents will be written "
            "to %s instead.",
            settings.s3_endpoint_url,
            exc,
            upload_dir,
        )
        return local

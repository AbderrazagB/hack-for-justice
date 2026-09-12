"""Upload validation.

Every rule here exists because the alternative is a real failure mode: an
unbounded upload fills the disk, a mislabelled document type crashes the rules
engine, and a declared Content-Type is attacker-controlled so it cannot be the
thing that decides what a file is.
"""

from __future__ import annotations

from fastapi import HTTPException, status

# A scanned filing page is well under this; a 25 MB upload is a mistake or an
# attack, not a document.
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_SUBMISSION = 12
MAX_TOTAL_BYTES = 40 * 1024 * 1024

# Signatures checked against the file's own first bytes, not its declared type.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"%PDF-", "application/pdf"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
)

ACCEPTED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/tiff", "image/webp", "application/pdf"}


def sniff_type(content: bytes) -> str | None:
    """Identify a file from its own bytes. None when unrecognised."""
    for signature, media_type in _MAGIC:
        if content.startswith(signature):
            return media_type

    # WEBP is RIFF....WEBP
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    return None


def validate_upload(content: bytes, filename: str) -> str:
    """Validate one uploaded file, returning its detected media type.

    Raises 400 or 413 with a message the applicant can act on.
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le fichier « {filename} » est vide.",
        )

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Le fichier « {filename} » dépasse "
                f"{MAX_FILE_BYTES // (1024 * 1024)} Mo."
            ),
        )

    detected = sniff_type(content)
    if detected is None or detected not in ACCEPTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le fichier « {filename} » n'est pas un format accepté. "
                "Formats acceptés : PDF, PNG, JPEG, TIFF, WEBP."
            ),
        )

    return detected


def validate_batch(total_files: int, total_bytes: int) -> None:
    if total_files > MAX_FILES_PER_SUBMISSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Au maximum {MAX_FILES_PER_SUBMISSION} fichiers par dépôt.",
        )

    if total_bytes > MAX_TOTAL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"L'ensemble des fichiers dépasse "
                f"{MAX_TOTAL_BYTES // (1024 * 1024)} Mo."
            ),
        )

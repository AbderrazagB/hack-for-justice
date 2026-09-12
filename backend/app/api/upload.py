from pathlib import Path
from shutil import copyfileobj
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter(tags=["upload"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload(file: Annotated[UploadFile, File(...)]) -> dict[str, str]:
    filename = Path(file.filename or "upload").name
    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    destination = RAW_DATA_DIR / filename
    with destination.open("wb") as output:
        copyfileobj(file.file, output)

    return {"filename": filename}

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.security import require_ops_api_key
from app.models.db import get_db, init_db
from app.services.document_service import ingest_document


router = APIRouter(prefix="/api/docs", tags=["docs"], dependencies=[Depends(require_ops_api_key)])
MAX_DOC_UPLOAD_BYTES = 4 * 1024 * 1024


@router.post("/ingest")
async def ingest_doc(
    file: UploadFile = File(...),
    doc_type: str = Form("knowledge"),
    category: str = Form(""),
    version: str = Form("v1"),
    db: Session = Depends(get_db),
) -> dict:
    init_db()
    raw = await file.read(MAX_DOC_UPLOAD_BYTES + 1)
    if len(raw) > MAX_DOC_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="document file is too large")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="document must be utf-8 text") from error
    return ingest_document(
        db,
        source_file=file.filename or "upload.txt",
        content=content,
        doc_type=doc_type,
        category=category,
        version=version,
    )

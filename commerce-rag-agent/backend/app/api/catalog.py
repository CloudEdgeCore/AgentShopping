from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.security import require_ops_api_key
from app.models.db import get_db, init_db
from app.services.catalog_import_service import IMPORT_DIR, import_catalog_csv
from app.services.index_job_service import rebuild_all_indexes


router = APIRouter(prefix="/api/catalog", tags=["catalog"], dependencies=[Depends(require_ops_api_key)])
MAX_CATALOG_UPLOAD_BYTES = 8 * 1024 * 1024

# JSON 数据集默认路径（相对于 backend/ 目录）
DEFAULT_DATASET_ROOT = Path("app/data/ecommerce_agent_dataset/ecommerce_agent_dataset")


@router.post("/import")
async def import_catalog(
    file: UploadFile = File(...),
    image_root: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    init_db()
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "catalog.csv").name
    if Path(filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="catalog import only accepts csv files")
    content = await file.read(MAX_CATALOG_UPLOAD_BYTES + 1)
    if len(content) > MAX_CATALOG_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="catalog file is too large")
    target = IMPORT_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
    target.write_bytes(content)
    return import_catalog_csv(
        db,
        target,
        image_root=Path(image_root) if image_root else target.parent,
    )


@router.post("/import-dataset")
def import_json_dataset(
    dataset_root: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    """导入 JSON 格式的电商数据集（100 个商品，4 个类目）。"""
    from app.services.json_dataset_import_service import import_json_product_dataset

    init_db()
    root = Path(dataset_root) if dataset_root else DEFAULT_DATASET_ROOT
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"Dataset path not found: {root}")
    return import_json_product_dataset(db, root)


@router.post("/reindex")
def reindex_catalog(db: Session = Depends(get_db)) -> dict:
    init_db()
    return rebuild_all_indexes(db)

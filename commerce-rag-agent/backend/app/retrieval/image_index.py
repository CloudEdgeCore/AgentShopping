import hashlib
import json
import os
from typing import Any

from sqlalchemy.orm import Session

from app.embeddings.chinese_clip import ChineseClipEmbedding
from app.models.tables import Product, ProductAttribute, ProductImage, ProductTag


PRODUCT_IMAGE_COLLECTION = "product_images"


class ImageIndex:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        embedding: ChineseClipEmbedding | None = None,
    ) -> None:
        self.chroma_path = chroma_path or os.getenv("CHROMA_PATH", "./app/data/chroma")
        self.embedding = embedding or ChineseClipEmbedding()
        self.client = None
        self.collection = None
        self._connect_client()

    def _connect_client(self) -> None:
        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            PRODUCT_IMAGE_COLLECTION,
            metadata=self._create_collection_metadata(),
        )

    def index_product_images(self, db: Session) -> None:
        rows = (
            db.query(ProductImage, Product)
            .join(Product, Product.id == ProductImage.product_id)
            .all()
        )
        if not rows:
            return
        product_ids = [product.id for image, product in rows]
        tags_by_product = _load_tags(db, product_ids)
        attributes_by_product = _load_attributes(db, product_ids)
        ids = [f"{product.id}:{image.id}" for image, product in rows]
        documents = [
            _product_image_document(
                product,
                tags=tags_by_product.get(product.id, []),
                attributes=attributes_by_product.get(product.id, {}),
            )
            for image, product in rows
        ]
        metadatas = [
            {
                "product_id": product.id,
                "image_id": image.id,
                "title": product.title,
                "image_url": image.image_url,
                "local_path": image.local_path,
                "is_primary": image.is_primary,
                "category": product.category,
                "subcategory": product.subcategory or "",
                "brand": product.brand,
                "price": product.price,
                "description": product.description,
                "specs_json": product.specs_json or "{}",
                "tags": " ".join(tags_by_product.get(product.id, [])),
                "attributes": " ".join(
                    f"{name}:{value}" for name, value in attributes_by_product.get(product.id, {}).items()
                ),
                "rating": product.rating,
                "sales": product.sales,
                "stock": product.stock,
            }
            for image, product in rows
        ]
        embeddings = [self.embedding.embed_image(image.local_path) for image, product in rows]
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        self._set_collection_metadata(self._collection_metadata(rows))

    def ensure_product_images_indexed(self, db: Session) -> None:
        rows = (
            db.query(ProductImage, Product)
            .join(Product, Product.id == ProductImage.product_id)
            .all()
        )
        if not rows:
            self._reset_if_collection_has_rows()
            return
        try:
            metadata = self.collection.metadata or {}
            expected_metadata = self._collection_metadata(rows)
            if self.collection.count() == len(rows) and _metadata_matches(metadata, expected_metadata):
                return
        except Exception:
            pass
        self.rebuild_product_images(db)

    def rebuild_product_images(self, db: Session) -> None:
        try:
            self.client.delete_collection(PRODUCT_IMAGE_COLLECTION)
        except Exception:
            pass
        self._connect_client()
        self.collection = self.client.get_or_create_collection(
            PRODUCT_IMAGE_COLLECTION,
            metadata=self._create_collection_metadata(),
        )
        self.index_product_images(db)

    def _set_collection_metadata(self, metadata: dict[str, Any]) -> None:
        self.collection.modify(metadata=metadata)

    def _reset_if_collection_has_rows(self) -> None:
        try:
            if self.collection.count() > 0:
                self.client.delete_collection(PRODUCT_IMAGE_COLLECTION)
                self._connect_client()
        except Exception:
            pass

    def search_by_image(self, image_path: str, *, limit: int = 8) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_image(image_path)],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        return _query_result_to_hits(result)

    def search_by_text(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_text(query)],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        return _query_result_to_hits(result)

    def _collection_metadata(self, rows: list[tuple[ProductImage, Product]]) -> dict[str, Any]:
        return {
            "kind": "product_image",
            "source": "sqlite_product_images",
            "image_count": len(rows),
            "fingerprint": product_images_fingerprint(rows),
            **self._embedding_metadata(),
        }

    def _create_collection_metadata(self) -> dict[str, str | int]:
        return {"hnsw:space": "cosine", **self._embedding_metadata()}

    def _embedding_metadata(self) -> dict[str, str | int]:
        signature = self.embedding.signature() if hasattr(self.embedding, "signature") else {}
        return {f"embedding_{key}": value for key, value in signature.items()}


def _query_result_to_hits(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {
            "id": ids[index],
            "text": documents[index] if index < len(documents) else "",
            "metadata": metadatas[index] if index < len(metadatas) else {},
            "distance": distances[index] if index < len(distances) else None,
            "image_similarity": _distance_to_similarity(distances[index] if index < len(distances) else None),
        }
        for index in range(len(ids))
    ]


def _distance_to_similarity(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return round(max(0.0, 1.0 - float(distance)), 6)


def _metadata_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(str(actual.get(key)) == str(value) for key, value in expected.items())


def _product_image_document(
    product: Product,
    *,
    tags: list[str],
    attributes: dict[str, str],
) -> str:
    return " ".join(
        str(value)
        for value in [
            product.title,
            product.category,
            product.subcategory or "",
            product.brand,
            product.description,
            product.specs_json or "",
            " ".join(tags),
            " ".join(f"{name}:{text}" for name, text in attributes.items()),
        ]
        if str(value or "").strip()
    )


def _load_tags(db: Session, product_ids: list[str]) -> dict[str, list[str]]:
    rows = db.query(ProductTag).filter(ProductTag.product_id.in_(product_ids)).all() if product_ids else []
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.product_id, []).append(str(row.value))
    return result


def _load_attributes(db: Session, product_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = db.query(ProductAttribute).filter(ProductAttribute.product_id.in_(product_ids)).all() if product_ids else []
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row.product_id, {})[str(row.name)] = str(row.value)
    return result


def product_images_fingerprint(rows: list[tuple[ProductImage, Product]]) -> str:
    payload_rows = [
        {
            "image_id": image.id,
            "product_id": image.product_id,
            "image_url": image.image_url,
            "local_path": image.local_path,
            "is_primary": image.is_primary,
            "title": product.title,
            "category": product.category,
            "subcategory": product.subcategory or "",
            "brand": product.brand,
            "description": product.description,
            "specs_json": product.specs_json or "{}",
            "price": product.price,
            "rating": product.rating,
            "sales": product.sales,
            "stock": product.stock,
        }
        for image, product in sorted(rows, key=lambda item: item[0].id)
    ]
    payload = json.dumps(payload_rows, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

import hashlib
import json
import os
from typing import Any

from sqlalchemy.orm import Session

from app.embeddings.bge_m3 import BgeM3Embedding
from app.models.tables import Product


PRODUCT_TEXT_COLLECTION = "product_text"
FAQ_COLLECTION = "faq"


DEFAULT_FAQS = [
    {
        "id": "faq_return_policy",
        "text": "退货政策：签收后 7 天内，商品不影响二次销售可申请无理由退货；质量问题支持售后检测。",
        "metadata": {"topic": "退货政策"},
    },
    {
        "id": "faq_warranty",
        "text": "保修政策：电子产品按品牌官方保修规则执行，平台提供订单凭证和售后协助。",
        "metadata": {"topic": "保修政策"},
    },
    {
        "id": "faq_invoice",
        "text": "发票说明：下单后可在订单详情申请电子发票，抬头支持个人或企业。",
        "metadata": {"topic": "发票"},
    },
]


class TextIndex:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        embedding: BgeM3Embedding | None = None,
    ) -> None:
        self.chroma_path = chroma_path or os.getenv("CHROMA_PATH", "./app/data/chroma")
        self.embedding = embedding or BgeM3Embedding()
        self.client = None
        self.product_collection = None
        self.faq_collection = None
        self._connect_client()

    def _connect_client(self) -> None:
        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.product_collection = self.client.get_or_create_collection(
            PRODUCT_TEXT_COLLECTION,
            metadata=self._create_collection_metadata(),
        )
        self.faq_collection = self.client.get_or_create_collection(
            FAQ_COLLECTION,
            metadata=self._create_collection_metadata(),
        )

    def index_products(self, db: Session, products: list[Product] | None = None) -> None:
        products = products if products is not None else db.query(Product).all()
        if not products:
            return
        ids = [product.id for product in products]
        documents = [product_to_text(product) for product in products]
        metadatas = [
            {
                "product_id": product.id,
                "title": product.title,
                "category": product.category,
                "subcategory": product.subcategory or "",
                "brand": product.brand,
                "price": product.price,
                "stock": product.stock,
            }
            for product in products
        ]
        self._upsert(self.product_collection, ids, documents, metadatas)
        self._set_collection_metadata(
            self.product_collection,
            {
                "kind": "product_text",
                "source": "sqlite_products",
                "product_count": len(products),
                "fingerprint": products_fingerprint(products),
                **self._embedding_metadata(),
            },
        )

    def ensure_products_indexed(self, db: Session) -> None:
        products = db.query(Product).all()
        if not products:
            self._reset_if_collection_has_rows(PRODUCT_TEXT_COLLECTION, self.product_collection)
            return
        try:
            metadata = self.product_collection.metadata or {}
            expected_metadata = self._product_collection_metadata(products)
            if self.product_collection.count() == len(products) and _metadata_matches(metadata, expected_metadata):
                return
        except Exception:
            pass
        self.rebuild_products(db, products=products)

    def rebuild_products(self, db: Session, products: list[Product] | None = None) -> None:
        self._reset_collection(PRODUCT_TEXT_COLLECTION)
        self.index_products(db, products=products)

    def index_faqs(self, faqs: list[dict[str, Any]] | None = None) -> None:
        rows = faqs or DEFAULT_FAQS
        expected_metadata = self._faq_collection_metadata(rows)
        self._ensure_collection_ready(FAQ_COLLECTION, self.faq_collection, len(rows), expected_metadata)
        self._upsert(
            self.faq_collection,
            [row["id"] for row in rows],
            [row["text"] for row in rows],
            [row["metadata"] for row in rows],
        )
        self._set_collection_metadata(self.faq_collection, expected_metadata)

    def rebuild_faqs(self, faqs: list[dict[str, Any]] | None = None) -> None:
        self._reset_collection(FAQ_COLLECTION)
        self.index_faqs(faqs)

    def search_products(
        self,
        query: str,
        *,
        limit: int = 5,
        product_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self._query(self.product_collection, query, limit, product_ids=product_ids)

    def search_faq(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        return self._query(self.faq_collection, query, limit)

    def _upsert(self, collection: Any, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=self.embedding.embed_documents(documents),
        )

    def _query(
        self,
        collection: Any,
        query: str,
        limit: int,
        *,
        product_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        where = None
        if product_ids:
            where = {"product_id": product_ids[0]} if len(product_ids) == 1 else {"product_id": {"$in": product_ids}}
        result = collection.query(
            query_embeddings=[self.embedding.embed_query(query)],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": result["ids"][0][index],
                "text": result["documents"][0][index],
                "metadata": result["metadatas"][0][index],
                "distance": result["distances"][0][index],
            }
            for index in range(len(result["ids"][0]))
        ]

    def _reset_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        self._connect_client()
        collection = self.client.get_or_create_collection(name, metadata=self._create_collection_metadata())
        if name == PRODUCT_TEXT_COLLECTION:
            self.product_collection = collection
        if name == FAQ_COLLECTION:
            self.faq_collection = collection

    def _ensure_collection_ready(
        self,
        name: str,
        collection: Any,
        expected_count: int,
        expected_metadata: dict[str, Any],
    ) -> None:
        try:
            metadata = collection.metadata or {}
            if collection.count() == expected_count and _metadata_matches(metadata, expected_metadata):
                return
        except Exception:
            pass
        self._reset_collection(name)

    def _reset_if_collection_has_rows(self, name: str, collection: Any) -> None:
        try:
            if collection.count() > 0:
                self._reset_collection(name)
        except Exception:
            pass

    def _set_collection_metadata(self, collection: Any, metadata: dict[str, Any]) -> None:
        collection.modify(metadata=metadata)

    def _product_collection_metadata(self, products: list[Product]) -> dict[str, Any]:
        return {
            "kind": "product_text",
            "source": "sqlite_products",
            "product_count": len(products),
            "fingerprint": products_fingerprint(products),
            **self._embedding_metadata(),
        }

    def _faq_collection_metadata(self, faqs: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "kind": "faq",
            "source": "default_faqs",
            "faq_count": len(faqs),
            "fingerprint": faqs_fingerprint(faqs),
            **self._embedding_metadata(),
        }

    def _create_collection_metadata(self) -> dict[str, str | int]:
        return {"hnsw:space": "cosine", **self._embedding_metadata()}

    def _embedding_metadata(self) -> dict[str, str | int]:
        signature = self.embedding.signature() if hasattr(self.embedding, "signature") else {}
        return {f"embedding_{key}": value for key, value in signature.items()}


def products_fingerprint(products: list[Product]) -> str:
    rows = [
        {
            "id": product.id,
            "title": product.title,
            "category": product.category,
            "subcategory": product.subcategory or "",
            "brand": product.brand,
            "price": product.price,
            "description": product.description,
            "specs_json": product.specs_json,
            "stock": product.stock,
        }
        for product in sorted(products, key=lambda item: item.id)
    ]
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def faqs_fingerprint(faqs: list[dict[str, Any]]) -> str:
    payload = json.dumps(faqs, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metadata_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(str(actual.get(key)) == str(value) for key, value in expected.items())


def product_to_text(product: Product) -> str:
    return (
        f"{product.title}\n"
        f"品类：{product.category}\n"
        f"子类目：{product.subcategory or ''}\n"
        f"品牌：{product.brand}\n"
        f"价格：{product.price}\n"
        f"描述：{product.description}\n"
        f"参数：{product.specs_json}"
    )

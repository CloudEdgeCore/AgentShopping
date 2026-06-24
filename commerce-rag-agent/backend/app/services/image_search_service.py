from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.retrieval.image_index import ImageIndex

SearchHits = list[dict[str, Any]]


class ImageSearchService:
    """图搜商品服务：封装多模态向量检索，支持以图搜图和文搜图。"""

    def __init__(self, chroma_path: str | None = None) -> None:
        self.chroma_path = chroma_path
        self._image_index: ImageIndex | None = None

    # ------------------------------------------------------------------
    # 内部惰性初始化
    # ------------------------------------------------------------------

    def _get_index(self) -> ImageIndex:
        if self._image_index is None:
            self._image_index = ImageIndex(chroma_path=self.chroma_path)
        return self._image_index

    def ensure_indexed(self, db: Session) -> None:
        """确保商品图片已写入向量库（幂等）。"""
        self._get_index().ensure_product_images_indexed(db)

    # ------------------------------------------------------------------
    # 以图搜图
    # ------------------------------------------------------------------

    def search_by_image(
        self,
        image_path: str,
        *,
        limit: int = 8,
    ) -> SearchHits:
        """上传一张图片，在 ChromaDB 中检索外观相似的商品图片。"""

        if not Path(image_path).exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        return self._get_index().search_by_image(
            image_path,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # 文搜图：用文字描述搜索商品图片
    # ------------------------------------------------------------------

    def search_by_text(
        self,
        query: str,
        *,
        limit: int = 8,
    ) -> SearchHits:
        """用文字描述在商品图片库中做语义检索。"""

        return self._get_index().search_by_text(query, limit=limit)

    # ------------------------------------------------------------------
    # 搜图 → 关联商品
    # ------------------------------------------------------------------

    def search_products_by_image(
        self,
        db: Session,
        image_path: str,
        *,
        limit: int = 8,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """以图搜图并聚合到商品维度。"""

        hits = self.search_by_image(
            image_path,
            limit=limit,
        )

        return self._aggregate_products(
            db,
            hits,
            source="image",
        )

    def search_products_by_text(
        self,
        db: Session,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """文搜图并聚合到商品维度。"""

        hits = self.search_by_text(
            query,
            limit=limit,
        )

        return self._aggregate_products(
            db,
            hits,
            source="text",
        )

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _aggregate_products(
        self,
        db: Session,
        hits: SearchHits,
        *,
        source: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """将图片命中去重聚合为商品列表。"""

        seen_product_ids: set[str] = set()
        products: list[dict[str, Any]] = []

        for hit in hits:
            metadata = hit.get("metadata") or {}
            product_id = metadata.get("product_id")

            if not product_id or product_id in seen_product_ids:
                continue

            seen_product_ids.add(product_id)

            products.append(
                {
                    "product_id": product_id,
                    "title": metadata.get("title", ""),
                    "image_url": metadata.get("image_url", ""),
                    "local_path": metadata.get("local_path", ""),
                    "category": metadata.get("category", ""),
                    "subcategory": metadata.get("subcategory", ""),
                    "brand": metadata.get("brand", ""),
                    "price": metadata.get("price", 0),
                    "rating": metadata.get("rating", 0),
                    "sales": metadata.get("sales", 0),
                    "stock": metadata.get("stock", 0),
                    "image_similarity": hit.get("image_similarity", 0.0),
                    "matched_image_id": metadata.get("image_id", ""),
                }
            )

        products.sort(
            key=lambda product: -float(product.get("image_similarity") or 0.0)
        )

        return products, {
            "retrieval_mode": f"image_search_{source}",
            "image_hits": len(hits),
            "product_hits": len(products),
            "top_similarity": round(products[0]["image_similarity"], 4)
            if products
            else 0.0,
        }

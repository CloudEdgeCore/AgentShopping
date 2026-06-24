from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_ops_api_key
from app.models.db import get_db, init_db
from app.models.tables import Product
from app.services.behavior_service import log_behavior_event
from app.services.product_intelligence_service import build_product_intelligence
from app.services.product_service import get_product_knowledge_docs
from app.services.review_qa_service import (
    answer_product_question,
    build_product_review_summary,
    create_product_question,
    create_product_review,
    list_product_questions,
)
from app.services.review_insight_service import build_review_insight, review_insight_payload
from app.services.user_product_service import add_product_to_list


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)) -> dict:
    """获取分类树（用于商品列表页筛选）。"""
    init_db()
    from sqlalchemy import func
    rows = db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    # 构建分类树：主分类 → 子分类
    category_map: dict[str, list[str]] = {}
    for product in db.query(Product).all():
        cat = product.category or ""
        sub = product.subcategory or ""
        if cat not in category_map:
            category_map[cat] = []
        if sub and sub not in category_map[cat]:
            category_map[cat].append(sub)
    tree = []
    for cat, count in rows:
        children = [{"id": f"{cat}_{sub}", "name": sub} for sub in category_map.get(cat, [])]
        tree.append({"id": cat, "name": cat, "children": children})
    return {"data": tree}


@router.get("/brands")
def get_brands(db: Session = Depends(get_db), categoryId: str | None = None, limit: int = 0) -> dict:
    """获取品牌列表（按商品数量降序，支持按分类过滤）。"""
    init_db()
    from sqlalchemy import func
    query = db.query(Product.brand, func.count(Product.id).label("cnt"))
    if categoryId:
        if "_" in categoryId:
            cat, sub = categoryId.split("_", 1)
            query = query.filter(Product.category == cat, Product.subcategory == sub)
        else:
            query = query.filter(Product.category == categoryId)
    rows = (
        query.group_by(Product.brand)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    brands = [{"id": brand, "name": brand, "count": cnt} for brand, cnt in rows if brand]
    if limit > 0:
        brands = brands[:limit]
    return {"data": brands}


@router.get("/page")
def get_product_page(
    current: int = 1,
    size: int = 12,
    categoryId: str | None = None,
    brandId: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """分页查询商品（兼容 Java 平台的 /search/product/page 接口格式）。"""
    init_db()
    from sqlalchemy import func, or_

    query = db.query(Product)

    # 分类筛选
    if categoryId:
        # categoryId 可能是主分类名（如"美妆护肤"）或"主分类_子分类"格式
        if "_" in categoryId:
            cat, sub = categoryId.split("_", 1)
            query = query.filter(Product.category == cat, Product.subcategory == sub)
        else:
            query = query.filter(Product.category == categoryId)

    # 品牌筛选
    if brandId:
        query = query.filter(Product.brand == brandId)

    # 关键词搜索
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.title.like(like_pattern),
                Product.brand.like(like_pattern),
                Product.category.like(like_pattern),
                Product.subcategory.like(like_pattern),
                Product.description.like(like_pattern),
            )
        )

    total = query.count()
    products = query.offset((current - 1) * size).limit(size).all()

    records = []
    for p in products:
        records.append({
            "spuId": p.id,
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "subcategory": p.subcategory or "",
            "brand": p.brand,
            "price": p.price,
            "image_url": p.image_url or "",
            "rating": p.rating,
            "sales": p.sales,
            "stock": p.stock,
        })

    return {"data": {"records": records, "total": total, "current": current, "size": size}}


class ProductReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str = Field(default="", max_length=2000)
    dimension_tags: list[str] = Field(default_factory=list, max_length=12)


class ProductQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class ProductQuestionAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


@router.get("/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "title": product.title,
        "category": product.category,
        "subcategory": product.subcategory or "",
        "brand": product.brand,
        "price": product.price,
        "description": product.description,
        "specs_json": product.specs_json,
        "rating": product.rating,
        "sales": product.sales,
        "stock": product.stock,
        "image_url": product.image_url,
    }


@router.get("/{product_id}/review-insights")
def get_product_review_insights(product_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    docs = get_product_knowledge_docs(db, product_id, limit=12)
    insight = build_review_insight(product, docs)
    return review_insight_payload(insight)


@router.get("/{product_id}/reviews/summary")
def get_product_reviews_summary(product_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return build_product_review_summary(db, product)


@router.post("/{product_id}/reviews")
def create_review(
    product_id: str,
    payload: ProductReviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    try:
        review = create_product_review(
            db,
            product_id=product_id,
            user_id=current_user.user_id,
            rating=payload.rating,
            content=payload.content,
            dimension_tags=payload.dimension_tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": review.id, "product_id": review.product_id, "rating": review.rating}


@router.get("/{product_id}/questions")
def get_product_questions(product_id: str, limit: int = 20, db: Session = Depends(get_db)) -> dict:
    init_db()
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return list_product_questions(db, product_id, limit=limit)


@router.post("/{product_id}/questions")
def create_question(
    product_id: str,
    payload: ProductQuestionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    try:
        question = create_product_question(
            db,
            product_id=product_id,
            user_id=current_user.user_id,
            question=payload.question,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": question.id, "product_id": question.product_id, "status": question.status}


@router.post("/{product_id}/questions/{question_id}/answer", dependencies=[Depends(require_ops_api_key)])
def answer_question(
    product_id: str,
    question_id: str,
    payload: ProductQuestionAnswerRequest,
    db: Session = Depends(get_db),
) -> dict:
    init_db()
    try:
        question = answer_product_question(
            db,
            question_id=question_id,
            product_id=product_id,
            answer=payload.answer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": question.id, "product_id": question.product_id, "status": question.status}


@router.post("/{product_id}/view")
def mark_product_view(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    try:
        result = add_product_to_list(
            db,
            user_id=current_user.user_id,
            product_id=product_id,
            list_type="recent",
            metadata={"source": "product_detail"},
        )
        log_behavior_event(
            db,
            event_type="product_detail_view",
            user_id=current_user.user_id,
            product_ids=[product_id],
            metadata={"source": "product_detail"},
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{product_id}/intelligence")
def get_product_intelligence(product_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    intelligence = build_product_intelligence(db, product_id)
    if not intelligence:
        raise HTTPException(status_code=404, detail="Product not found")
    return intelligence

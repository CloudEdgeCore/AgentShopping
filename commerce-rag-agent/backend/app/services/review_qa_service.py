import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product, ProductQuestion, ProductReview
from app.services.product_service import get_product_knowledge_docs
from app.services.review_insight_service import build_review_insight, review_insight_payload


POSITIVE_KEYWORDS = ["好用", "舒服", "耐用", "清爽", "续航", "性价比", "稳定", "轻便", "满意", "推荐"]
RISK_KEYWORDS = ["偏大", "偏小", "闷", "重", "贵", "慢", "一般", "失望", "异味", "掉"]


def create_product_review(
    db: Session,
    *,
    product_id: str,
    user_id: str,
    rating: int,
    content: str = "",
    dimension_tags: list[str] | None = None,
) -> ProductReview:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("Product not found")
    review = ProductReview(
        id=f"rev_{uuid.uuid4().hex[:12]}",
        product_id=product_id,
        user_id=user_id,
        rating=max(min(int(rating), 5), 1),
        content=str(content or "").strip()[:2000],
        dimension_tags_json=json.dumps(dimension_tags or [], ensure_ascii=False),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def build_product_review_summary(db: Session, product: Product) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(ProductReview)
            .where(ProductReview.product_id == product.id)
            .where(ProductReview.moderation_status == "approved")
            .order_by(ProductReview.created_at.desc())
            .limit(200)
        ).all()
    )
    docs = get_product_knowledge_docs(db, product.id, limit=12)
    fallback_insight = review_insight_payload(build_review_insight(product, docs))
    histogram = {str(score): 0 for score in range(5, 0, -1)}
    dimension_counts: dict[str, Counter[str]] = defaultdict(Counter)
    positive_tags: Counter[str] = Counter()
    risk_tags: Counter[str] = Counter()

    for row in rows:
        histogram[str(row.rating)] = histogram.get(str(row.rating), 0) + 1
        tags = _review_tags(row)
        polarity = "positive" if row.rating >= 4 else "negative" if row.rating <= 2 else "neutral"
        for tag in tags:
            dimension_counts[tag][polarity] += 1
        positive_tags.update(_keyword_hits(row.content, POSITIVE_KEYWORDS))
        risk_tags.update(_keyword_hits(row.content, RISK_KEYWORDS))

    if not rows:
        for point in fallback_insight.get("positive_points", []):
            positive_tags[str(point)] += 1
        for point in fallback_insight.get("risk_points", []):
            risk_tags[str(point)] += 1
        for name, status in (fallback_insight.get("dimensions") or {}).items():
            dimension_counts[str(name)][str(status)] += 1

    avg_rating = round(sum(row.rating for row in rows) / len(rows), 2) if rows else round(float(product.rating or 0), 2)
    return {
        "product_id": product.id,
        "title": product.title,
        "total_reviews": len(rows),
        "avg_rating": avg_rating,
        "rating_histogram": histogram,
        "positive_tags": _counter_payload(positive_tags),
        "risk_tags": _counter_payload(risk_tags),
        "dimensions": _dimension_payload(dimension_counts),
        "representative_reviews": [_review_payload(row) for row in rows[:5]],
        "insight": fallback_insight,
        "source": "reviews" if rows else "knowledge_fallback",
    }


def create_product_question(
    db: Session,
    *,
    product_id: str,
    user_id: str,
    question: str,
) -> ProductQuestion:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("Product not found")
    row = ProductQuestion(
        id=f"qa_{uuid.uuid4().hex[:12]}",
        product_id=product_id,
        user_id=user_id,
        question=str(question or "").strip()[:1000],
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def answer_product_question(
    db: Session,
    *,
    question_id: str,
    answer: str,
    product_id: str | None = None,
) -> ProductQuestion:
    row = db.get(ProductQuestion, question_id)
    if not row:
        raise ValueError("Question not found")
    if product_id and row.product_id != product_id:
        raise ValueError("Question does not belong to product")
    row.answer = str(answer or "").strip()[:2000]
    row.status = "answered" if row.answer else "pending"
    row.answered_at = datetime.now(UTC).replace(tzinfo=None) if row.answer else None
    db.commit()
    db.refresh(row)
    return row


def list_product_questions(db: Session, product_id: str, *, limit: int = 20) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(ProductQuestion)
            .where(ProductQuestion.product_id == product_id)
            .order_by(ProductQuestion.status.desc(), ProductQuestion.created_at.desc())
            .limit(max(min(limit, 100), 1))
        ).all()
    )
    return {
        "product_id": product_id,
        "questions": [_question_payload(row) for row in rows],
        "pending_count": sum(1 for row in rows if row.status == "pending"),
    }


def _review_payload(row: ProductReview) -> dict[str, Any]:
    return {
        "id": row.id,
        "rating": row.rating,
        "content": row.content,
        "dimension_tags": _review_tags(row),
        "source": row.source,
        "created_at": row.created_at.isoformat(),
    }


def _question_payload(row: ProductQuestion) -> dict[str, Any]:
    return {
        "id": row.id,
        "question": row.question,
        "answer": row.answer,
        "status": row.status,
        "helpful_count": row.helpful_count,
        "created_at": row.created_at.isoformat(),
        "answered_at": row.answered_at.isoformat() if row.answered_at else "",
    }


def _review_tags(row: ProductReview) -> list[str]:
    try:
        parsed = json.loads(row.dimension_tags_json or "[]")
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        return [str(key).strip() for key, value in parsed.items() if value and str(key).strip()]
    return []


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in str(text or "")]


def _counter_payload(counter: Counter[str], *, limit: int = 8) -> list[dict[str, Any]]:
    return [{"tag": key, "count": count} for key, count in counter.most_common(limit)]


def _dimension_payload(dimensions: dict[str, Counter[str]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, counts in dimensions.items():
        total = sum(counts.values())
        positive = counts.get("positive", 0)
        negative = counts.get("negative", 0)
        if positive > negative:
            sentiment = "positive"
        elif negative > positive:
            sentiment = "negative"
        else:
            sentiment = "mixed"
        result.append(
            {
                "name": name,
                "total": total,
                "positive": positive,
                "negative": negative,
                "sentiment": sentiment,
            }
        )
    return sorted(result, key=lambda item: (-int(item["total"]), str(item["name"])))[:10]


def extract_dimension_tags(text: str) -> list[str]:
    clean = str(text or "").strip()
    if not clean:
        return []
    tokens = [item for item in re.split(r"[\s,，、;；]+", clean) if item]
    return list(dict.fromkeys(tokens))[:12]

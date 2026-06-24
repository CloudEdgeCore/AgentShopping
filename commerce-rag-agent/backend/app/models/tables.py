from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """用户表（与 Java 平台 ums_user 共享结构）。"""
    __tablename__ = "rag_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    mobile: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    avatar_url: Mapped[str] = mapped_column(String(300), default="")
    gender: Mapped[int] = mapped_column(Integer, default=0)
    user_type: Mapped[int] = mapped_column(Integer, default=1)  # 1=普通用户, 2=管理员
    status: Mapped[int] = mapped_column(Integer, default=1)  # 0=禁用, 1=启用
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Product(Base):
    __tablename__ = "rag_products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subcategory: Mapped[str] = mapped_column(String(64), index=True, default="")
    brand: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    specs_json: Mapped[str] = mapped_column(Text, default="{}")
    rating: Mapped[float] = mapped_column(Float, default=0)
    sales: Mapped[int] = mapped_column(Integer, default=0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str] = mapped_column(String(300), default="")


class ProductImage(Base):
    __tablename__ = "rag_product_images"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(300), nullable=False)
    local_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ProductSku(Base):
    __tablename__ = "rag_product_skus"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specs_json: Mapped[str] = mapped_column(Text, default="{}")
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str] = mapped_column(String(300), default="")


class ProductAttribute(Base):
    __tablename__ = "rag_product_attributes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)


class ProductTag(Base):
    __tablename__ = "rag_product_tags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    tag_type: Mapped[str] = mapped_column(String(64), default="tag")
    value: Mapped[str] = mapped_column(String(100), nullable=False)


class ProductReview(Base):
    __tablename__ = "rag_product_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    rating: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    dimension_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(64), default="user")
    moderation_status: Mapped[str] = mapped_column(String(32), index=True, default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ProductQuestion(Base):
    __tablename__ = "rag_product_questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserProductCollection(Base):
    __tablename__ = "rag_user_product_collections"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", "list_type", name="uq_rag_user_product_collection"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    list_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Order(Base):
    __tablename__ = "rag_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    checkout_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0)
    payable_amount: Mapped[int] = mapped_column(Integer, default=0)
    address_id: Mapped[str] = mapped_column(String(64), default="addr_default")
    payment_url: Mapped[str] = mapped_column(String(300), default="")
    payment_status: Mapped[str] = mapped_column(String(64), index=True, default="pending")
    payment_provider: Mapped[str] = mapped_column(String(64), default="")
    payment_transaction_id: Mapped[str] = mapped_column(String(128), default="")
    idempotency_key: Mapped[str] = mapped_column(String(128), index=True, default="")
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    logistics_status: Mapped[str] = mapped_column(String(200), default="")
    return_status: Mapped[str] = mapped_column(String(200), default="")
    shipping_recipient_name: Mapped[str] = mapped_column(String(100), default="")
    shipping_phone: Mapped[str] = mapped_column(String(32), default="")
    shipping_address: Mapped[str] = mapped_column(String(500), default="")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class OrderItem(Base):
    __tablename__ = "rag_order_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("rag_orders.id"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    sku_id: Mapped[str] = mapped_column(String(64), default="")
    title_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    specs_json: Mapped[str] = mapped_column(Text, default="{}")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CartItem(Base):
    __tablename__ = "rag_cart_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    sku_id: Mapped[str] = mapped_column(String(64), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_specs_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CheckoutSession(Base):
    __tablename__ = "rag_checkout_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    subtotal_amount: Mapped[int] = mapped_column(Integer, default=0)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    shipping_fee: Mapped[int] = mapped_column(Integer, default=0)
    payable_amount: Mapped[int] = mapped_column(Integer, default=0)
    address_id: Mapped[str] = mapped_column(String(64), default="addr_default")
    confirm_token: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class StockReservation(Base):
    __tablename__ = "rag_stock_reservations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checkout_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    sku_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), index=True, default="reserved")
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PaymentCallbackLog(Base):
    __tablename__ = "rag_payment_callback_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True, default="")
    event_id: Mapped[str] = mapped_column(String(128), index=True, default="")
    order_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    transaction_id: Mapped[str] = mapped_column(String(128), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="received")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CommerceOutboxEvent(Base):
    __tablename__ = "rag_commerce_outbox_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CommerceAuditLog(Base):
    __tablename__ = "rag_commerce_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    session_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    product_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PriceAlert(Base):
    __tablename__ = "rag_price_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("rag_products.id"), index=True, nullable=False)
    target_price: Mapped[int] = mapped_column(Integer, nullable=False)
    current_price_snapshot: Mapped[int] = mapped_column(Integer, default=0)
    alert_type: Mapped[str] = mapped_column(String(32), default="price_drop")
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class UserPreference(Base):
    __tablename__ = "rag_user_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), index=True, default="global")
    key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    value_json: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[str] = mapped_column(String(64), default="agent")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ChatSession(Base):
    __tablename__ = "rag_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Message(Base):
    __tablename__ = "rag_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("rag_sessions.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Document(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(300), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[str] = mapped_column(String(64), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ImportJob(Base):
    __tablename__ = "rag_import_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IndexJob(Base):
    __tablename__ = "rag_index_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    product_text_count: Mapped[int] = mapped_column(Integer, default=0)
    knowledge_docs_count: Mapped[int] = mapped_column(Integer, default=0)
    product_images_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Feedback(Base):
    __tablename__ = "rag_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("rag_messages.id"), index=True, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RetrievalLog(Base):
    __tablename__ = "rag_retrieval_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(64), nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, default="{}")
    candidates_json: Mapped[str] = mapped_column(Text, default="[]")
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
    retrieval_mode: Mapped[str] = mapped_column(String(64), index=True, default="")
    llm_errors_json: Mapped[str] = mapped_column(Text, default="[]")
    provider_latency_json: Mapped[str] = mapped_column(Text, default="{}")
    cost_estimate_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), index=True, default="success")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RecommendationLog(Base):
    __tablename__ = "rag_recommendation_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    products_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class UserBehaviorEvent(Base):
    __tablename__ = "rag_user_behavior_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    message_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    product_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

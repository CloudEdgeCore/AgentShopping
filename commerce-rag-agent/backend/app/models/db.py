import json
import os
import threading
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:123456@127.0.0.1:3306/shopping?charset=utf8mb4")

# SQLite 需要 check_same_thread=False，MySQL 不需要
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

_db_initialized = False
_db_initialized_lock = threading.Lock()


def init_db() -> None:
    """创建所有表并执行增量迁移（进程内只执行一次，线程安全）。"""
    global _db_initialized
    if _db_initialized:
        return
    with _db_initialized_lock:
        if _db_initialized:
            return
        # SQLite 需要先创建目录
        if DATABASE_URL.startswith("sqlite:///"):
            db_path = Path(urlparse(DATABASE_URL).path.lstrip("/"))
            db_path.parent.mkdir(parents=True, exist_ok=True)

        Base.metadata.create_all(bind=engine)
        _migrate_product_subcategory()
        _migrate_order_checkout_columns()
        _migrate_order_safety_columns()
        _migrate_observability_columns()
        _migrate_payment_callback_columns()
        _migrate_product_experience_tables()
        _db_initialized = True


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _table_exists(table_name: str) -> bool:
    """检查表是否存在（兼容 SQLite 和 MySQL）。"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在（兼容 SQLite 和 MySQL）。"""
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def _index_exists(table_name: str, index_name: str) -> bool:
    """检查索引是否存在（兼容 SQLite 和 MySQL）。"""
    inspector = inspect(engine)
    indexes = inspector.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def _migrate_product_subcategory() -> None:
    if not _table_exists("rag_products"):
        return

    with engine.begin() as connection:
        if not _column_exists("rag_products", "subcategory"):
            connection.execute(text("ALTER TABLE rag_products ADD COLUMN subcategory VARCHAR(64) DEFAULT ''"))

        rows = connection.execute(
            text("SELECT id, title, category, subcategory, brand FROM rag_products")
        ).mappings()
        taxonomy = _load_taxonomy_for_migration()
        for row in rows:
            category, subcategory = _normalize_product_taxonomy_for_migration(
                category=str(row.get("category") or ""),
                subcategory=str(row.get("subcategory") or ""),
                title=str(row.get("title") or ""),
                brand=str(row.get("brand") or ""),
                taxonomy=taxonomy,
            )
            if category != row.get("category") or subcategory != (row.get("subcategory") or ""):
                connection.execute(
                    text("UPDATE rag_products SET category = :category, subcategory = :subcategory WHERE id = :id"),
                    {"id": row["id"], "category": category, "subcategory": subcategory},
                )


def _migrate_order_checkout_columns() -> None:
    if not _table_exists("rag_orders"):
        return

    migrations = {
        "checkout_id": "ALTER TABLE rag_orders ADD COLUMN checkout_id VARCHAR(64) DEFAULT ''",
        "total_amount": "ALTER TABLE rag_orders ADD COLUMN total_amount INTEGER DEFAULT 0",
        "payable_amount": "ALTER TABLE rag_orders ADD COLUMN payable_amount INTEGER DEFAULT 0",
        "address_id": "ALTER TABLE rag_orders ADD COLUMN address_id VARCHAR(64) DEFAULT 'addr_default'",
        "payment_url": "ALTER TABLE rag_orders ADD COLUMN payment_url VARCHAR(300) DEFAULT ''",
        "items_json": "ALTER TABLE rag_orders ADD COLUMN items_json TEXT DEFAULT '[]'",
    }
    with engine.begin() as connection:
        for column, ddl in migrations.items():
            if not _column_exists("rag_orders", column):
                connection.execute(text(ddl))


def _migrate_order_safety_columns() -> None:
    with engine.begin() as connection:
        if _table_exists("rag_orders"):
            migrations = {
                "payment_status": "ALTER TABLE rag_orders ADD COLUMN payment_status VARCHAR(64) DEFAULT 'pending'",
                "payment_provider": "ALTER TABLE rag_orders ADD COLUMN payment_provider VARCHAR(64) DEFAULT ''",
                "payment_transaction_id": "ALTER TABLE rag_orders ADD COLUMN payment_transaction_id VARCHAR(128) DEFAULT ''",
                "idempotency_key": "ALTER TABLE rag_orders ADD COLUMN idempotency_key VARCHAR(128) DEFAULT ''",
                "paid_at": "ALTER TABLE rag_orders ADD COLUMN paid_at DATETIME",
                "updated_at": "ALTER TABLE rag_orders ADD COLUMN updated_at DATETIME",
            }
            for column, ddl in migrations.items():
                if not _column_exists("rag_orders", column):
                    connection.execute(text(ddl))
            # 创建唯一索引（MySQL 不支持 WHERE 条件索引，使用普通唯一索引）
            if not _index_exists("rag_orders", "uq_rag_orders_user_idempotency_key"):
                try:
                    connection.execute(
                        text(
                            "CREATE UNIQUE INDEX uq_rag_orders_user_idempotency_key "
                            "ON rag_orders(user_id, idempotency_key)"
                        )
                    )
                except Exception:
                    pass  # 索引可能因重复数据失败，忽略

        if _table_exists("rag_checkout_sessions"):
            if not _column_exists("rag_checkout_sessions", "expires_at"):
                connection.execute(text("ALTER TABLE rag_checkout_sessions ADD COLUMN expires_at DATETIME"))


def _migrate_observability_columns() -> None:
    migrations_by_table = {
        "rag_retrieval_logs": {
            "trace_id": "ALTER TABLE rag_retrieval_logs ADD COLUMN trace_id VARCHAR(64) DEFAULT ''",
            "trace_json": "ALTER TABLE rag_retrieval_logs ADD COLUMN trace_json TEXT DEFAULT '[]'",
            "retrieval_mode": "ALTER TABLE rag_retrieval_logs ADD COLUMN retrieval_mode VARCHAR(64) DEFAULT ''",
            "llm_errors_json": "ALTER TABLE rag_retrieval_logs ADD COLUMN llm_errors_json TEXT DEFAULT '[]'",
            "provider_latency_json": "ALTER TABLE rag_retrieval_logs ADD COLUMN provider_latency_json TEXT DEFAULT '{}'",
            "cost_estimate_json": "ALTER TABLE rag_retrieval_logs ADD COLUMN cost_estimate_json TEXT DEFAULT '{}'",
            "status": "ALTER TABLE rag_retrieval_logs ADD COLUMN status VARCHAR(32) DEFAULT 'success'",
            "latency_ms": "ALTER TABLE rag_retrieval_logs ADD COLUMN latency_ms INTEGER DEFAULT 0",
            "error": "ALTER TABLE rag_retrieval_logs ADD COLUMN error TEXT DEFAULT ''",
        },
        "rag_recommendation_logs": {
            "trace_id": "ALTER TABLE rag_recommendation_logs ADD COLUMN trace_id VARCHAR(64) DEFAULT ''",
        },
        "rag_user_behavior_events": {
            "trace_id": "ALTER TABLE rag_user_behavior_events ADD COLUMN trace_id VARCHAR(64) DEFAULT ''",
        },
        "rag_commerce_audit_logs": {
            "trace_id": "ALTER TABLE rag_commerce_audit_logs ADD COLUMN trace_id VARCHAR(64) DEFAULT ''",
        },
    }
    with engine.begin() as connection:
        for table_name, migrations in migrations_by_table.items():
            if not _table_exists(table_name):
                continue
            for column, ddl in migrations.items():
                if not _column_exists(table_name, column):
                    connection.execute(text(ddl))


def _migrate_payment_callback_columns() -> None:
    if not _table_exists("rag_payment_callback_logs"):
        return
    if not _index_exists("rag_payment_callback_logs", "uq_rag_payment_callbacks_provider_event"):
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_rag_payment_callbacks_provider_event "
                        "ON rag_payment_callback_logs(provider, event_id)"
                    )
                )
        except Exception:
            pass


def _migrate_product_experience_tables() -> None:
    if not _table_exists("rag_user_product_collections"):
        return
    if not _index_exists("rag_user_product_collections", "uq_rag_user_product_collection"):
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_rag_user_product_collection "
                        "ON rag_user_product_collections(user_id, product_id, list_type)"
                    )
                )
        except Exception:
            pass


def _load_taxonomy_for_migration() -> dict:
    taxonomy_path = Path(__file__).resolve().parents[1] / "data" / "taxonomy.json"
    try:
        return json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"categories": []}


def _normalize_product_taxonomy_for_migration(
    *,
    category: str,
    subcategory: str,
    title: str,
    brand: str,
    taxonomy: dict,
) -> tuple[str, str]:
    subcategory_match = _match_subcategory_alias(subcategory, taxonomy, exact=True)
    category_as_subcategory = _match_subcategory_alias(category, taxonomy, exact=True)
    text_match = _match_subcategory_alias(" ".join([title, brand, category, subcategory]), taxonomy, exact=False)
    top_category = _match_category_alias(category, taxonomy)

    matched = subcategory_match or category_as_subcategory or text_match
    if matched:
        return matched[0], matched[1]
    if top_category:
        return top_category, subcategory.strip()
    return category.strip(), subcategory.strip()


def _match_category_alias(value: str, taxonomy: dict) -> str | None:
    normalized_value = value.strip().lower()
    if not normalized_value:
        return None
    for category in taxonomy.get("categories", []):
        aliases = [category.get("name", ""), *category.get("aliases", [])]
        if any(normalized_value == str(alias).lower() for alias in aliases):
            return str(category.get("name") or "").strip() or None
    return None


def _match_subcategory_alias(value: str, taxonomy: dict, *, exact: bool) -> tuple[str, str] | None:
    normalized_value = value.strip().lower()
    if not normalized_value:
        return None

    best: tuple[int, str, str] | None = None
    for category in taxonomy.get("categories", []):
        category_name = str(category.get("name") or "").strip()
        for subcategory in category.get("subcategories", []):
            subcategory_name = str(subcategory.get("name") or "").strip()
            for alias in [subcategory_name, *subcategory.get("aliases", [])]:
                normalized_alias = str(alias).strip().lower()
                if not normalized_alias:
                    continue
                matched = normalized_value == normalized_alias if exact else normalized_alias in normalized_value
                if matched and (best is None or len(normalized_alias) > best[0]):
                    best = (len(normalized_alias), category_name, subcategory_name)
    return (best[1], best[2]) if best else None

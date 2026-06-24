import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.models.tables import UserPreference


PROFILE_FIELDS = ["audience", "use_cases", "preferences", "budget_max"]


def memory_with_profile_defaults(db: Session, *, user_id: str, query: str, memory: dict | None) -> dict:
    base_memory = dict(memory or {})
    constraints = extract_shopping_constraints(query).model_dump()
    profile = get_user_profile(db, user_id=user_id)
    next_memory = dict(base_memory)
    next_memory["user_profile"] = profile

    category = constraints.get("category") or base_memory.get("category")
    subcategory = constraints.get("subcategory") or base_memory.get("subcategory")
    if not category:
        return next_memory

    scoped = _find_scoped_profile(profile, category=category, subcategory=subcategory)
    for field in PROFILE_FIELDS:
        if constraints.get(field) or base_memory.get(field):
            continue
        value = scoped.get(field)
        if value:
            next_memory[field] = value
    return next_memory


def update_profile_from_memory(
    db: Session,
    *,
    user_id: str,
    memory: dict | None,
    source: str = "agent",
) -> dict[str, Any]:
    memory = memory or {}
    category = str(memory.get("category") or "").strip()
    subcategory = str(memory.get("subcategory") or "").strip()
    if category:
        scoped_value = {
            field: memory[field]
            for field in PROFILE_FIELDS
            if memory.get(field) not in (None, "", [], {})
        }
        if scoped_value:
            upsert_preference(
                db,
                user_id=user_id,
                scope=_scope_key(category, subcategory),
                key="shopping_context",
                value=scoped_value,
                source=source,
            )

    global_value: dict[str, Any] = {}
    if memory.get("audience"):
        global_value["audience"] = memory["audience"]
    if memory.get("preferences"):
        global_value["preferences"] = list(dict.fromkeys(str(item) for item in memory["preferences"] if item))
    if global_value:
        upsert_preference(
            db,
            user_id=user_id,
            scope="global",
            key="shopping_context",
            value=global_value,
            source=source,
        )
    return get_user_profile(db, user_id=user_id)


def get_user_profile(db: Session, *, user_id: str) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(UserPreference)
            .where(UserPreference.user_id == user_id)
            .order_by(UserPreference.updated_at.desc())
        ).all()
    )
    profile: dict[str, Any] = {
        "user_id": user_id,
        "global": {},
        "scoped": {},
        "updated_at": None,
    }
    for row in rows:
        value = _safe_json_dict(row.value_json)
        if row.scope == "global":
            profile["global"].update(value)
        else:
            profile["scoped"][row.scope] = value
        if profile["updated_at"] is None or row.updated_at.isoformat() > profile["updated_at"]:
            profile["updated_at"] = row.updated_at.isoformat()
    return profile


def upsert_preference(
    db: Session,
    *,
    user_id: str,
    scope: str,
    key: str,
    value: dict[str, Any],
    source: str = "user",
) -> UserPreference:
    existing = db.scalar(
        select(UserPreference)
        .where(UserPreference.user_id == user_id)
        .where(UserPreference.scope == scope)
        .where(UserPreference.key == key)
    )
    if existing:
        existing.value_json = json.dumps(value, ensure_ascii=False)
        existing.source = source
        existing.updated_at = datetime.now(UTC)
        row = existing
    else:
        row = UserPreference(
            id=f"pref_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            scope=scope,
            key=key,
            value_json=json.dumps(value, ensure_ascii=False),
            source=source,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_user_profile(db: Session, *, user_id: str) -> int:
    result = db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
    db.commit()
    return int(result.rowcount or 0)


def _find_scoped_profile(profile: dict[str, Any], *, category: str, subcategory: str | None) -> dict[str, Any]:
    exact_key = _scope_key(category, subcategory or "")
    category_key = _scope_key(category, "")
    scoped = profile.get("scoped") or {}
    return dict(scoped.get(exact_key) or scoped.get(category_key) or {})


def _scope_key(category: str, subcategory: str | None = "") -> str:
    clean_category = category.strip()
    clean_subcategory = (subcategory or "").strip() or "*"
    return f"category:{clean_category}:{clean_subcategory}"


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}

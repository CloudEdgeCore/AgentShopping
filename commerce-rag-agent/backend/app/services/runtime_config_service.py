import json
import os
import importlib.util
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.db import DATABASE_URL
from app.models.tables import Product, ProductImage
from app.retrieval.image_index import PRODUCT_IMAGE_COLLECTION
from app.retrieval.text_index import FAQ_COLLECTION, PRODUCT_TEXT_COLLECTION


Check = dict[str, Any]


def runtime_health(db: Session | None = None, *, deep: bool = False) -> dict[str, Any]:
    checks = [
        _database_check(db),
        _rules_file_check(),
        _taxonomy_file_check(),
        _provider_config_check("llm", "LLM_ENABLED", ["DOUBAO_BASE_URL", "DOUBAO_MODEL"], ["DOUBAO_API_KEY", "ARK_API_KEY"]),
        _provider_config_check("asr", "ASR_PROVIDER", ["ASR_BASE_URL", "ASR_MODEL"], ["ASR_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY"]),
        _provider_config_check("tts", "TTS_PROVIDER", ["TTS_BASE_URL", "TTS_MODEL", "TTS_VOICE"], ["TTS_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY", "OPENAI_API_KEY"]),
        _provider_config_check("vlm", "VLM_PROVIDER", ["VLM_BASE_URL", "VLM_MODEL"], ["VLM_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY"]),
        _embedding_config_check(),
        _auth_check(),
        _cors_check(),
        _rate_limit_check(),
        _ops_auth_check(),
        _payment_webhook_check(),
        _migration_check(),
    ]
    if deep:
        checks.append(_chroma_check())
        checks.extend(_provider_probe_checks())
        if db is not None:
            checks.append(_catalog_check(db))
    status = _rollup_status(checks)
    return {
        "status": status,
        "deep": deep,
        "checks": checks,
    }


def config_summary(db: Session | None = None) -> dict[str, Any]:
    health = runtime_health(db, deep=True)
    return {
        **health,
        "environment": {
            "database_url": _safe_database_url(DATABASE_URL),
            "chroma_path": _chroma_path(),
            "commerce_rules_path": _rules_path(),
            "cors_allow_origins": _split_env("CORS_ALLOW_ORIGINS"),
            "rate_limit_enabled": _env_bool("RATE_LIMIT_ENABLED", True),
            "rate_limit_per_minute": _env_int("RATE_LIMIT_PER_MINUTE", 120),
            "ops_api_key_configured": bool(_env_first("OPS_API_KEY")),
            "auth_required": _env_bool("AUTH_REQUIRED", True),
            "trusted_auth_header_enabled": _trusted_auth_header_enabled(),
            "trusted_auth_header_signature_required": _trusted_auth_header_signature_required(),
            "payment_webhook_secret_configured": bool(_env_first("PAYMENT_WEBHOOK_SECRET")),
            "provider_probes_enabled": _env_bool("HEALTH_PROVIDER_PROBES_ENABLED", False),
        },
    }


def _database_check(db: Session | None) -> Check:
    if db is None:
        return _check("database", "warn", "database session not provided")
    try:
        db.execute(text("SELECT 1"))
        return _check("database", "ok", "database connection is healthy", database_url=_safe_database_url(DATABASE_URL))
    except Exception as error:
        return _check("database", "error", _format_error(error), database_url=_safe_database_url(DATABASE_URL))


def _rules_file_check() -> Check:
    path = Path(_rules_path())
    if not path.exists():
        return _check("commerce_rules", "error", "commerce rules file is missing", path=str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return _check("commerce_rules", "error", _format_error(error), path=str(path))
    if not isinstance(payload, dict) or not payload:
        return _check("commerce_rules", "error", "commerce rules file is empty or invalid", path=str(path))
    return _check("commerce_rules", "ok", "commerce rules file is valid", path=str(path), sections=sorted(payload.keys()))


def _taxonomy_file_check() -> Check:
    path = Path(__file__).resolve().parents[1] / "data" / "taxonomy.json"
    if not path.exists():
        return _check("taxonomy", "error", "taxonomy file is missing", path=str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return _check("taxonomy", "error", _format_error(error), path=str(path))
    categories = payload.get("categories") if isinstance(payload, dict) else None
    if not isinstance(categories, list) or not categories:
        return _check("taxonomy", "error", "taxonomy has no categories", path=str(path))
    return _check("taxonomy", "ok", "taxonomy file is valid", path=str(path), category_count=len(categories))


def _provider_config_check(name: str, provider_env: str, required_envs: list[str], key_envs: list[str]) -> Check:
    provider = os.getenv(provider_env, "").strip()
    enabled = _provider_enabled(provider_env, provider)
    if not enabled:
        return _check(name, "warn", f"{name} provider is disabled", provider=provider or "disabled")

    missing = [env for env in required_envs if not _env_first(env)]
    key_configured = bool(_env_first(*key_envs))
    if not key_configured:
        missing.append("api_key")
    if missing:
        return _check(
            name,
            "warn",
            f"{name} provider is enabled but not fully configured",
            provider=provider or "enabled",
            missing=missing,
        )
    return _check(
        name,
        "ok",
        f"{name} provider is configured",
        provider=provider or "enabled",
        required={env: bool(_env_first(env)) for env in required_envs},
        api_key_configured=True,
    )


def _embedding_config_check() -> Check:
    text_provider = (os.getenv("TEXT_EMBEDDING_PROVIDER") or os.getenv("EMBEDDING_PROVIDER") or "bge_m3").strip()
    image_provider = (os.getenv("IMAGE_EMBEDDING_PROVIDER") or "chinese_clip").strip()
    missing: list[str] = []
    if text_provider.lower() in {"volcengine", "ark", "cloud", "doubao"}:
        for env in ["ARK_EMBEDDING_BASE_URL", "ARK_TEXT_EMBEDDING_MODEL"]:
            if not _env_first(env):
                missing.append(env)
        if not _env_first("ARK_EMBEDDING_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY"):
            missing.append("embedding_api_key")
    else:
        if importlib.util.find_spec("FlagEmbedding") is None:
            missing.append("FlagEmbedding")

    if image_provider.lower() in {"volcengine", "ark", "cloud", "doubao"}:
        for env in ["ARK_EMBEDDING_BASE_URL", "ARK_MULTIMODAL_EMBEDDING_MODEL"]:
            if not _env_first(env):
                missing.append(env)
        if not _env_first("ARK_EMBEDDING_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY"):
            missing.append("multimodal_embedding_api_key")
    elif image_provider.lower() in {"chinese_clip", "chinese-clip", "clip", "local"}:
        if importlib.util.find_spec("torch") is None or importlib.util.find_spec("transformers") is None:
            missing.append("torch/transformers")

    if missing:
        return _check(
            "embedding",
            "warn",
            "embedding providers are not fully configured",
            text_provider=text_provider,
            image_provider=image_provider,
            missing=sorted(set(missing)),
        )
    return _check(
        "embedding",
        "ok",
        "embedding providers are configured",
        text_provider=text_provider,
        image_provider=image_provider,
    )


def _provider_probe_checks() -> list[Check]:
    if not _env_bool("HEALTH_PROVIDER_PROBES_ENABLED", False):
        return [
            _check(
                "provider_probes",
                "warn",
                "provider runtime probes are disabled; set HEALTH_PROVIDER_PROBES_ENABLED=true to call external providers",
            )
        ]
    checks = [
        _llm_probe_check(),
        _embedding_probe_check(),
        _vlm_probe_check(),
        _asr_probe_check(),
        _tts_probe_check(),
    ]
    return checks


def _llm_probe_check() -> Check:
    import time

    try:
        from app.llm.openai_compatible_client import OpenAICompatibleClient

        started_at = time.perf_counter()
        client = OpenAICompatibleClient(timeout=float(os.getenv("HEALTH_PROVIDER_PROBE_TIMEOUT_SECONDS", "5")))
        content = client.chat_sync(
            [{"role": "user", "content": "health check: reply ok"}],
            temperature=0,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if not content:
            return _check("llm_probe", "error", "LLM provider returned empty response", latency_ms=latency_ms)
        return _check("llm_probe", "ok", "LLM provider responded", latency_ms=latency_ms, model=client.model)
    except Exception as error:
        return _check("llm_probe", "error", _format_error(error))


def _embedding_probe_check() -> Check:
    import time

    try:
        from app.embeddings.bge_m3 import BgeM3Embedding

        started_at = time.perf_counter()
        embedding = BgeM3Embedding()
        vector = embedding.embed_query("健康检查")
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if not vector:
            return _check("embedding_probe", "error", "embedding provider returned empty vector", latency_ms=latency_ms)
        return _check(
            "embedding_probe",
            "ok",
            "embedding provider returned a vector",
            latency_ms=latency_ms,
            provider=embedding.provider,
            model=embedding.model_name,
            dimension=len(vector),
        )
    except Exception as error:
        return _check("embedding_probe", "error", _format_error(error))


def _vlm_probe_check() -> Check:
    try:
        from app.services.vision_service import vision_capabilities

        capabilities = vision_capabilities()
        if not capabilities.get("configured"):
            return _check("vlm_probe", "warn", "VLM provider is not configured", **capabilities)
        return _check("vlm_probe", "ok", "VLM provider configuration is usable", **capabilities)
    except Exception as error:
        return _check("vlm_probe", "error", _format_error(error))


def _asr_probe_check() -> Check:
    try:
        from app.services.voice_service import voice_capabilities

        capabilities = voice_capabilities()
        asr = capabilities.get("asr", {}) if isinstance(capabilities, dict) else {}
        if not asr.get("configured"):
            return _check("asr_probe", "warn", "ASR provider is not configured", capabilities=asr)
        return _check("asr_probe", "ok", "ASR provider configuration is usable", capabilities=asr)
    except Exception as error:
        return _check("asr_probe", "error", _format_error(error))


def _tts_probe_check() -> Check:
    try:
        from app.services.voice_service import voice_capabilities

        capabilities = voice_capabilities()
        tts = capabilities.get("tts", {}) if isinstance(capabilities, dict) else {}
        if not tts.get("configured"):
            return _check("tts_probe", "warn", "TTS provider is not configured", capabilities=tts)
        return _check("tts_probe", "ok", "TTS provider configuration is usable", capabilities=tts)
    except Exception as error:
        return _check("tts_probe", "error", _format_error(error))


def _chroma_check() -> Check:
    path = _chroma_path()
    try:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
        collections = _collection_names(client.list_collections())
        counts = {}
        peeked = {}
        for name in [PRODUCT_TEXT_COLLECTION, PRODUCT_IMAGE_COLLECTION, FAQ_COLLECTION]:
            if name in collections:
                collection = client.get_collection(name)
                counts[name] = collection.count()
                if counts[name] > 0:
                    try:
                        peeked[name] = bool(collection.peek(limit=1).get("ids"))
                    except Exception:
                        peeked[name] = False
        missing = [name for name in [PRODUCT_TEXT_COLLECTION, PRODUCT_IMAGE_COLLECTION] if name not in collections]
        status = "warn" if missing else "ok"
        return _check(
            "chroma",
            status,
            "chroma is reachable" if not missing else "chroma is reachable but important collections are missing",
            path=path,
            collections=collections,
            counts=counts,
            read_probe=peeked,
            missing=missing,
        )
    except Exception as error:
        return _check("chroma", "error", _format_error(error), path=path)


def _catalog_check(db: Session) -> Check:
    try:
        product_count = int(db.query(Product).count())
        image_count = int(db.query(ProductImage).count())
    except Exception as error:
        return _check("catalog", "error", _format_error(error))
    if product_count <= 0:
        return _check("catalog", "error", "catalog has no products", product_count=product_count, product_images=image_count)
    if image_count <= 0:
        return _check("catalog", "warn", "catalog has products but no product images", product_count=product_count, product_images=image_count)
    return _check("catalog", "ok", "catalog has products and images", product_count=product_count, product_images=image_count)


def _cors_check() -> Check:
    origins = _split_env("CORS_ALLOW_ORIGINS")
    if not origins:
        return _check("cors", "warn", "CORS_ALLOW_ORIGINS is empty")
    if "*" in origins:
        return _check("cors", "warn", "wildcard CORS is not recommended", origins=origins)
    return _check("cors", "ok", "CORS origins are configured", origins=origins)


def _rate_limit_check() -> Check:
    if not _env_bool("RATE_LIMIT_ENABLED", True):
        return _check("rate_limit", "warn", "rate limiting is disabled")
    return _check(
        "rate_limit",
        "ok",
        "rate limiting is enabled",
        limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 120),
    )


def _auth_check() -> Check:
    if not _env_bool("AUTH_REQUIRED", True):
        return _check("auth", "warn", "AUTH_REQUIRED is disabled; user isolation falls back to DEV_USER_ID")
    if _dev_auto_login_enabled():
        return _check(
            "auth",
            "warn",
            "dev auto login is enabled for local testing",
            auto_user_id=os.getenv("DEV_AUTO_USER_ID", "test-user-001"),
            auto_roles=_split_env_value(os.getenv("DEV_AUTO_USER_ROLES", "user,ops")),
        )
    if _env_first("APP_USER_TOKENS"):
        return _check(
            "auth",
            "ok",
            "request authentication is enabled",
            token_mapping_configured=True,
            trusted_auth_header_enabled=_trusted_auth_header_enabled(),
        )
    if _trusted_auth_header_enabled():
        if _trusted_auth_header_signature_required() and not _env_first("TRUSTED_AUTH_HEADER_SECRET"):
            return _check(
                "auth",
                "error",
                "trusted auth headers require TRUSTED_AUTH_HEADER_SECRET in production",
                trusted_auth_header_enabled=True,
                signature_required=True,
            )
        return _check(
            "auth",
            "warn" if not _trusted_auth_header_signature_required() else "ok",
            "trusted auth headers are enabled",
            token_mapping_configured=False,
            trusted_auth_header_enabled=True,
            signature_required=_trusted_auth_header_signature_required(),
        )
    return _check("auth", "error", "AUTH_REQUIRED is enabled but no token mapping or trusted auth header is configured")


def _ops_auth_check() -> Check:
    if _env_first("OPS_API_KEY"):
        return _check("ops_auth", "ok", "ops api key is configured")
    if _env_first("APP_USER_TOKENS") or _trusted_auth_header_enabled() or _dev_auto_login_enabled():
        return _check("ops_auth", "warn", "OPS_API_KEY is not configured; ops endpoints require an ops/admin user token")
    return _check("ops_auth", "error", "OPS_API_KEY or ops/admin user auth is required for ops endpoints")


def _payment_webhook_check() -> Check:
    provider = os.getenv("PAYMENT_PROVIDER", "manual").strip() or "manual"
    mock_enabled = _env_bool("PAYMENT_MOCK_ENABLED", False)
    checkout_url_configured = bool(_env_first("PAYMENT_CHECKOUT_URL_TEMPLATE"))
    if _is_production() and mock_enabled:
        return _check("payment_webhook", "error", "mock payment is enabled in production", provider=provider)
    if _env_first("PAYMENT_WEBHOOK_SECRET"):
        return _check(
            "payment_webhook",
            "ok",
            "payment webhook signature secret is configured",
            provider=provider,
            mock_enabled=mock_enabled,
            checkout_url_configured=checkout_url_configured,
        )
    return _check(
        "payment_webhook",
        "error" if _is_production() else "warn",
        "PAYMENT_WEBHOOK_SECRET is not configured; payment callbacks must stay behind ops auth",
        provider=provider,
        mock_enabled=mock_enabled,
        checkout_url_configured=checkout_url_configured,
    )


def _migration_check() -> Check:
    has_alembic = (Path.cwd() / "alembic").exists() or (Path.cwd() / "migrations").exists()
    if has_alembic:
        return _check("schema_migrations", "ok", "versioned schema migrations are present")
    return _check(
        "schema_migrations",
        "warn",
        "schema currently uses create_all/lightweight ALTER migrations; add Alembic before production",
        database_url=_safe_database_url(DATABASE_URL),
    )


def _check(name: str, status: str, message: str, **details: Any) -> Check:
    payload: Check = {"name": name, "status": status, "message": message}
    payload.update(details)
    return payload


def _rollup_status(checks: list[Check]) -> str:
    if any(check.get("status") == "error" for check in checks):
        return "error"
    if any(check.get("status") == "warn" for check in checks):
        return "warn"
    return "ok"


def _provider_enabled(provider_env: str, provider: str) -> bool:
    if provider_env == "LLM_ENABLED":
        return _env_bool("LLM_ENABLED", True)
    return provider.strip().lower() not in {"", "disabled", "none", "off", "false", "0"}


def _trusted_auth_header_enabled() -> bool:
    return _env_bool("TRUSTED_AUTH_HEADER_ENABLED", not _is_production())


def _trusted_auth_header_signature_required() -> bool:
    return bool(_env_first("TRUSTED_AUTH_HEADER_SECRET")) or _env_bool(
        "TRUSTED_AUTH_HEADER_REQUIRE_SIGNATURE",
        _is_production(),
    )


def _is_production() -> bool:
    value = _env_first("APP_ENV", "ENVIRONMENT", "FASTAPI_ENV").lower()
    return value in {"prod", "production"}


def _rules_path() -> str:
    return os.getenv("COMMERCE_RULES_PATH") or str(Path(__file__).resolve().parents[1] / "data" / "commerce_rules.json")


def _chroma_path() -> str:
    return os.getenv("CHROMA_PATH", "./app/data/chroma")


def _collection_names(collections: list[Any]) -> list[str]:
    names = []
    for collection in collections:
        names.append(collection if isinstance(collection, str) else str(getattr(collection, "name", "")))
    return sorted(name for name in names if name)


def _safe_database_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    _, host = rest.rsplit("@", 1)
    return f"{scheme}://***@{host}"


def _split_env(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _split_env_value(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _env_first(*names: str) -> str:
    for name in names:
        value = _resolve_env_reference(os.getenv(name, ""))
        if value:
            return value
    return ""


def _resolve_env_reference(value: str) -> str:
    text_value = str(value or "").strip()
    if text_value.startswith("${") and text_value.endswith("}"):
        return os.getenv(text_value[2:-1], "").strip()
    return text_value


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _dev_auto_login_enabled() -> bool:
    return (not _is_production()) and _env_bool("DEV_AUTO_LOGIN_ENABLED", True)


def _format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {str(error)[:240]}"

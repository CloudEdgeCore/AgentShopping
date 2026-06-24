import os
from typing import Any, Protocol

from dotenv import load_dotenv

from app.embeddings.cloud_embeddings import ArkEmbeddingClient


DEFAULT_BGE_M3_MODEL = "BAAI/bge-m3"
_LOCAL_BGE_M3_BACKENDS: dict[tuple[str, str, bool, bool, int, int], "LocalBgeM3Backend"] = {}


class TextEmbeddingBackend(Protocol):
    provider: str
    model_name: str
    dimension: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...


class BgeM3Embedding:
    """Text embedding adapter for product and knowledge retrieval.

    Supported providers:
    - ``bge_m3`` / ``local``: local FlagEmbedding BGEM3FlagModel.
    - ``volcengine`` / ``ark`` / ``cloud``: Ark embedding fallback.
    """

    def __init__(
        self,
        dimension: int | None = None,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        local_files_only: bool | None = None,
        use_fp16: bool | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
    ) -> None:
        load_dotenv()
        resolved_provider = _normalize_provider(
            provider
            or os.getenv("TEXT_EMBEDDING_PROVIDER")
            or os.getenv("EMBEDDING_PROVIDER")
            or "bge_m3"
        )
        if resolved_provider == "bge_m3":
            self.backend: TextEmbeddingBackend = _get_local_bge_m3_backend(
                model_name=model_name,
                device=device,
                local_files_only=local_files_only,
                use_fp16=use_fp16,
                batch_size=batch_size,
                max_length=max_length,
            )
        elif resolved_provider == "volcengine":
            self.backend = ArkTextEmbeddingBackend(dimension=dimension)
        else:
            raise ValueError(f"Unsupported text embedding provider: {resolved_provider}")

        self.provider = self.backend.provider
        self.model_name = self.backend.model_name
        self.dimension = self.backend.dimension

    def embed_query(self, text: str) -> list[float]:
        return self.backend.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.backend.embed_documents(texts)

    def signature(self) -> dict[str, str | int]:
        return {
            "provider": self.provider,
            "model": self.model_name,
            "dimension": self.dimension,
        }


class ArkTextEmbeddingBackend:
    provider = "volcengine"

    def __init__(self, *, dimension: int | None = None) -> None:
        self.client = ArkEmbeddingClient()
        self.model_name = self.client.text_model
        self.dimension = dimension or int(os.getenv("ARK_TEXT_EMBEDDING_DIMENSION", "2048"))

    def embed_query(self, text: str) -> list[float]:
        return self.client.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed_texts(texts)


class LocalBgeM3Backend:
    provider = "bge_m3"

    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        local_files_only: bool,
        use_fp16: bool,
        batch_size: int,
        max_length: int,
    ) -> None:
        if local_files_only:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        os.environ.setdefault("TQDM_DISABLE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as error:  # pragma: no cover - depends on optional local embedding stack
            raise RuntimeError(
                "Local BGE-M3 requires FlagEmbedding. Install project dependencies or use TEXT_EMBEDDING_PROVIDER=volcengine."
            ) from error
        _patch_multiprocess_resource_tracker()

        self.model_name = model_name
        self.device = device
        self.local_files_only = local_files_only
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.max_length = max_length
        self.dimension = int(os.getenv("BGE_M3_DIMENSION", "1024"))

        cache_dir = os.getenv("BGE_M3_CACHE_DIR") or None
        try:
            self.model = BGEM3FlagModel(
                self.model_name,
                normalize_embeddings=True,
                use_fp16=self.use_fp16,
                devices=self.device,
                cache_dir=cache_dir,
                batch_size=self.batch_size,
                query_max_length=self.max_length,
                passage_max_length=self.max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
        except Exception as error:  # pragma: no cover - depends on local model files / network
            raise RuntimeError(
                f"Cannot load BGE-M3 model '{self.model_name}'. "
                "Set BGE_M3_LOCAL_DIR to a downloaded model directory, "
                "or set BGE_M3_LOCAL_FILES_ONLY=false for first-time download."
            ) from error

    def embed_query(self, text: str) -> list[float]:
        return self._encode([_safe_text(text)])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode([_safe_text(text) for text in texts])

    def _encode(self, texts: list[str]) -> list[list[float]]:
        result = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense = result["dense_vecs"] if isinstance(result, dict) else result
        vectors = _vectors_to_lists(dense)
        if vectors:
            self.dimension = len(vectors[0])
        return vectors


def _get_local_bge_m3_backend(
    *,
    model_name: str | None,
    device: str | None,
    local_files_only: bool | None,
    use_fp16: bool | None,
    batch_size: int | None,
    max_length: int | None,
) -> LocalBgeM3Backend:
    resolved_model = _resolve_model_name(model_name)
    resolved_device = device or os.getenv("BGE_M3_DEVICE") or "cpu"
    resolved_local_files_only = _resolve_local_files_only(local_files_only)
    resolved_use_fp16 = _resolve_use_fp16(use_fp16, resolved_device)
    resolved_batch_size = batch_size or int(os.getenv("BGE_M3_BATCH_SIZE", "16"))
    resolved_max_length = max_length or int(os.getenv("BGE_M3_MAX_LENGTH", "512"))
    cache_key = (
        resolved_model,
        resolved_device,
        resolved_local_files_only,
        resolved_use_fp16,
        resolved_batch_size,
        resolved_max_length,
    )
    backend = _LOCAL_BGE_M3_BACKENDS.get(cache_key)
    if backend is None:
        backend = LocalBgeM3Backend(
            model_name=resolved_model,
            device=resolved_device,
            local_files_only=resolved_local_files_only,
            use_fp16=resolved_use_fp16,
            batch_size=resolved_batch_size,
            max_length=resolved_max_length,
        )
        _LOCAL_BGE_M3_BACKENDS[cache_key] = backend
    return backend


def _resolve_model_name(model_name: str | None) -> str:
    return (
        model_name
        or os.getenv("BGE_M3_LOCAL_DIR")
        or os.getenv("BGE_M3_MODEL_NAME")
        or DEFAULT_BGE_M3_MODEL
    )


def _resolve_local_files_only(local_files_only: bool | None) -> bool:
    return _env_bool("BGE_M3_LOCAL_FILES_ONLY", False) if local_files_only is None else local_files_only


def _resolve_use_fp16(use_fp16: bool | None, device: str) -> bool:
    if use_fp16 is not None:
        return use_fp16
    if device.lower() == "cpu":
        return False
    return _env_bool("BGE_M3_USE_FP16", True)


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized in {"local", "bge", "bge_m3", "bge-m3", "baai_bge_m3"}:
        return "bge_m3"
    if normalized in {"volcengine", "ark", "cloud", "doubao"}:
        return "volcengine"
    return normalized


def _safe_text(text: str) -> str:
    return (text or "").strip() or " "


def _vectors_to_lists(vectors: Any) -> list[list[float]]:
    if hasattr(vectors, "ndim") and vectors.ndim == 1:
        vectors = [vectors]
    return [
        [float(value) for value in (vector.tolist() if hasattr(vector, "tolist") else vector)]
        for vector in vectors
    ]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _patch_multiprocess_resource_tracker() -> None:
    try:
        import multiprocess.resource_tracker as resource_tracker
    except Exception:
        return

    original = getattr(resource_tracker.ResourceTracker, "__del__", None)
    if original is None or getattr(original, "_commerce_safe_patch", False):
        return

    def safe_del(self: Any) -> None:
        try:
            original(self)
        except AttributeError as error:
            if "_recursion_count" not in str(error):
                raise

    safe_del._commerce_safe_patch = True  # type: ignore[attr-defined]
    resource_tracker.ResourceTracker.__del__ = safe_del

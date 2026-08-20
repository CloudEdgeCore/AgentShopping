import os
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

from app.embeddings.cloud_embeddings import ArkEmbeddingClient


DEFAULT_CHINESE_CLIP_MODEL = ""
_LOCAL_CHINESE_CLIP_BACKENDS: dict[tuple[str, str, bool], "LocalChineseClipBackend"] = {}
_SIGLIP2_BACKENDS: dict[tuple[str, str, bool], "Siglip2EmbeddingBackend"] = {}


class ImageTextEmbeddingBackend(Protocol):
    provider: str
    model_name: str
    dimension: int

    def embed_image(self, path: str) -> list[float]:
        ...

    def embed_text(self, text: str) -> list[float]:
        ...


class ChineseClipEmbedding:
    """Image/text embedding adapter for product image retrieval.

    Supported providers:
    - ``chinese_clip`` / ``local``: local Transformers ChineseCLIPModel.
    - ``siglip2`` / ``siglip``: local Transformers SigLIP2 model (e.g. google/siglip2-base-patch16-224).
    - ``siglip_server``: HTTP SigLIP2 embedding service (serve_siglip2.py).
    - ``volcengine`` / ``ark`` / ``cloud``: existing Ark multimodal embedding.

    The public methods stay stable for the rest of the project:
    - ``embed_image(path)``
    - ``embed_text(text)``
    """

    def __init__(
        self,
        dimension: int | None = None,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        load_dotenv()
        resolved_provider = _normalize_provider(
            provider
            or os.getenv("CHINESE_CLIP_PROVIDER")
            or os.getenv("IMAGE_EMBEDDING_PROVIDER")
            or "volcengine"
        )
        if resolved_provider == "chinese_clip":
            self.backend: ImageTextEmbeddingBackend = _get_local_chinese_clip_backend(
                model_name=model_name,
                device=device,
                local_files_only=local_files_only,
            )
        elif resolved_provider == "siglip2":
            self.backend = _get_siglip2_backend(
                model_name=model_name,
                device=device,
                local_files_only=local_files_only,
            )
        elif resolved_provider == "siglip_server":
            self.backend = SiglipServerEmbeddingBackend()
        elif resolved_provider == "volcengine":
            self.backend = ArkMultimodalEmbeddingBackend(dimension=dimension)
        else:
            raise ValueError(f"Unsupported image embedding provider: {resolved_provider}")

        self.provider = self.backend.provider
        self.model_name = self.backend.model_name
        self.dimension = self.backend.dimension

    def embed_image(self, path: str) -> list[float]:
        return self.backend.embed_image(path)

    def embed_text(self, text: str) -> list[float]:
        return self.backend.embed_text(text)

    def signature(self) -> dict[str, str | int]:
        return {
            "provider": self.provider,
            "model": self.model_name,
            "dimension": self.dimension,
        }


class ArkMultimodalEmbeddingBackend:
    provider = "volcengine"

    def __init__(self, *, dimension: int | None = None) -> None:
        self.client = ArkEmbeddingClient()
        self.model_name = self.client.multimodal_model
        self.dimension = dimension or int(os.getenv("ARK_EMBEDDING_DIMENSION", "2048"))

    def embed_image(self, path: str) -> list[float]:
        return self.client.embed_image_path(path)

    def embed_text(self, text: str) -> list[float]:
        return self.client.embed_multimodal_text(text)


class LocalChineseClipBackend:
    provider = "chinese_clip"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        device: str | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        try:
            import torch
            from PIL import Image
            from transformers import ChineseCLIPModel, ChineseCLIPProcessor
        except ImportError as error:  # pragma: no cover - depends on optional local model stack
            raise RuntimeError(
                "Local Chinese-CLIP requires torch, pillow and transformers. "
                "Install the chinese-clip optional dependencies or use IMAGE_EMBEDDING_PROVIDER=volcengine."
            ) from error

        self.torch = torch
        self.image_cls = Image
        self.model_name = (
            model_name
            or os.getenv("CHINESE_CLIP_LOCAL_DIR")
            or os.getenv("CHINESE_CLIP_MODEL_NAME")
            or DEFAULT_CHINESE_CLIP_MODEL
        )
        if not self.model_name:
            raise RuntimeError("CHINESE_CLIP_MODEL_NAME or CHINESE_CLIP_LOCAL_DIR is required")
        self.local_files_only = _env_bool("CHINESE_CLIP_LOCAL_FILES_ONLY", False) if local_files_only is None else local_files_only
        self.device = device or os.getenv("CHINESE_CLIP_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")

        model_source = str(Path(self.model_name)) if Path(self.model_name).exists() else self.model_name
        try:
            self.processor = ChineseCLIPProcessor.from_pretrained(
                model_source,
                local_files_only=self.local_files_only,
            )
            self.model = ChineseCLIPModel.from_pretrained(
                model_source,
                local_files_only=self.local_files_only,
                use_safetensors=False,
            ).to(self.device)
        except Exception as error:  # pragma: no cover - depends on local model files / network
            raise RuntimeError(
                f"Cannot load Chinese-CLIP model '{self.model_name}'. "
                "Set CHINESE_CLIP_LOCAL_DIR to a downloaded model directory, "
                "set CHINESE_CLIP_LOCAL_FILES_ONLY=false for first-time download, "
                "or set IMAGE_EMBEDDING_PROVIDER=volcengine."
            ) from error

        self.model.eval()
        self.dimension = int(getattr(self.model.config, "projection_dim", 512))

    def embed_image(self, path: str) -> list[float]:
        image_path = Path(path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        image = self.image_cls.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = self._to_device(inputs)
        with self.torch.no_grad():
            features = self.model.get_image_features(**inputs)
        features = self._project_if_needed(features, self.model.visual_projection)
        return self._normalize(features)

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must not be empty")

        inputs = self.processor(text=[text], padding=True, truncation=True, return_tensors="pt")
        inputs = self._to_device(inputs)
        with self.torch.no_grad():
            features = self.model.get_text_features(**inputs)
        features = self._project_if_needed(features, self.model.text_projection)
        return self._normalize(features)

    def _to_device(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {key: value.to(self.device) if hasattr(value, "to") else value for key, value in inputs.items()}

    def _project_if_needed(self, features: Any, projection: Any) -> Any:
        if hasattr(features, "pooler_output"):
            pooled = features.pooler_output
            if getattr(projection, "in_features", None) == pooled.shape[-1]:
                return projection(pooled)
            return pooled
        return features

    def _normalize(self, features: Any) -> list[float]:
        vector = features.detach().float().cpu()
        if vector.ndim > 1:
            vector = vector.reshape(vector.shape[0], -1)[0]
        norm = self.torch.linalg.vector_norm(vector)
        if float(norm) > 0:
            vector = vector / norm
        return [float(value) for value in vector.tolist()]


class Siglip2EmbeddingBackend:
    """本地 SigLIP2 图文嵌入后端（transformers AutoModel/AutoProcessor）。

    与 Chinese-CLIP 完全兼容的外部接口（embed_image / embed_text），
    支持多语言（含中文），中文电商图搜可替代 Chinese-CLIP。
    """

    provider = "siglip2"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        device: str | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        try:
            import torch
            from PIL import Image
            from transformers import AutoModel, AutoProcessor
        except ImportError as error:  # pragma: no cover - depends on optional local model stack
            raise RuntimeError(
                "Local SigLIP2 requires torch, pillow and transformers>=4.52. "
                "Install the chinese-clip optional dependencies or use IMAGE_EMBEDDING_PROVIDER=volcengine."
            ) from error

        self.torch = torch
        self.image_cls = Image
        self.model_name = (
            model_name
            or os.getenv("CHINESE_CLIP_LOCAL_DIR")
            or os.getenv("CHINESE_CLIP_MODEL_NAME")
            or ""
        )
        if not self.model_name:
            raise RuntimeError("CHINESE_CLIP_LOCAL_DIR or CHINESE_CLIP_MODEL_NAME is required for SigLIP2")
        self.local_files_only = _env_bool("CHINESE_CLIP_LOCAL_FILES_ONLY", False) if local_files_only is None else local_files_only
        self.device = device or os.getenv("CHINESE_CLIP_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")

        model_source = str(Path(self.model_name)) if Path(self.model_name).exists() else self.model_name
        try:
            self.processor = AutoProcessor.from_pretrained(
                model_source,
                local_files_only=self.local_files_only,
            )
            self.model = AutoModel.from_pretrained(
                model_source,
                local_files_only=self.local_files_only,
            ).to(self.device)
        except Exception as error:  # pragma: no cover - depends on local model files
            raise RuntimeError(
                f"Cannot load SigLIP2 model '{self.model_name}'. "
                "Make sure the directory contains config.json / model.safetensors (or set "
                "CHINESE_CLIP_LOCAL_FILES_ONLY=false for first-time download), "
                "or set IMAGE_EMBEDDING_PROVIDER=volcengine."
            ) from error

        self.model.eval()
        self.dimension = _siglip2_dimension(self.model)

    def embed_image(self, path: str) -> list[float]:
        image_path = Path(path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        image = self.image_cls.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = self._to_device(inputs)
        with self.torch.no_grad():
            features = self.model.get_image_features(**inputs)
        return self._normalize(features)

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must not be empty")

        inputs = self.processor(text=[text], padding=True, truncation=True, return_tensors="pt")
        inputs = self._to_device(inputs)
        with self.torch.no_grad():
            features = self.model.get_text_features(**inputs)
        return self._normalize(features)

    def _to_device(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {key: value.to(self.device) if hasattr(value, "to") else value for key, value in inputs.items()}

    def _normalize(self, features: Any) -> list[float]:
        vector = features.detach().float().cpu()
        if vector.ndim > 1:
            vector = vector.reshape(vector.shape[0], -1)[0]
        norm = self.torch.linalg.vector_norm(vector)
        if float(norm) > 0:
            vector = vector / norm
        return [float(value) for value in vector.tolist()]


def _get_siglip2_backend(
    *,
    model_name: str | None,
    device: str | None,
    local_files_only: bool | None,
) -> Siglip2EmbeddingBackend:
    resolved_model = _resolve_local_model_name(model_name)
    resolved_device = _resolve_local_device(device)
    resolved_local_files_only = _resolve_local_files_only(local_files_only)
    cache_key = (resolved_model, resolved_device, resolved_local_files_only)
    backend = _SIGLIP2_BACKENDS.get(cache_key)
    if backend is None:
        backend = Siglip2EmbeddingBackend(
            model_name=resolved_model,
            device=resolved_device,
            local_files_only=resolved_local_files_only,
        )
        _SIGLIP2_BACKENDS[cache_key] = backend
    return backend


def _siglip2_dimension(model: Any) -> int:
    projection_dim = getattr(model.config, "projection_dim", None)
    if projection_dim:
        return int(projection_dim)
    text_config = getattr(model.config, "text_config", None)
    if text_config is not None and getattr(text_config, "hidden_size", None):
        return int(text_config.hidden_size)
    return 768


class SiglipServerEmbeddingBackend:
    """HTTP 远程 SigLIP2 嵌入后端（对接 serve_siglip2.py 部署的服务）。

    配置：
    - IMAGE_EMBEDDING_BASE_URL：服务地址，如 http://127.0.0.1:8002
    - IMAGE_EMBEDDING_MODEL：模型名，默认 siglip2
    - IMAGE_EMBEDDING_API_KEY：可选
    """

    provider = "siglip_server"

    def __init__(self) -> None:
        import requests
        from dotenv import load_dotenv

        load_dotenv()
        self._requests = requests
        self.base_url = os.getenv("IMAGE_EMBEDDING_BASE_URL", "http://127.0.0.1:8002").strip().rstrip("/")
        self.model_name = os.getenv("IMAGE_EMBEDDING_MODEL", "siglip2").strip() or "siglip2"
        self.api_key = os.getenv("IMAGE_EMBEDDING_API_KEY", "").strip()
        self.timeout = float(os.getenv("IMAGE_EMBEDDING_TIMEOUT_SECONDS", "60"))
        self.dimension = int(os.getenv("IMAGE_EMBEDDING_DIMENSION", "0") or 0)

    def embed_image(self, path: str) -> list[float]:
        import base64
        import mimetypes
        from pathlib import Path

        image_path = Path(path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        payload = {
            "model": self.model_name,
            "image": f"data:{mime_type};base64,{encoded}",
        }
        vector = self._post("/v1/images/embeddings", payload)[0]
        self._sync_dimension(vector)
        return vector

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must not be empty")
        payload = {"model": self.model_name, "input": [text]}
        vector = self._post("/v1/embeddings", payload)[0]
        self._sync_dimension(vector)
        return vector

    def _post(self, path: str, payload: dict[str, Any]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self._requests.post(
                f"{self.base_url}{path}",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except self._requests.RequestException as error:
            raise RuntimeError(f"SigLIP2 server request failed ({self.base_url}{path}): {error}") from error
        if response.status_code >= 400:
            raise RuntimeError(
                f"SigLIP2 server error {response.status_code}: {response.text[:500]}"
            )
        data = response.json()
        items = data.get("data") or []
        vectors: list[list[float]] = []
        for item in items:
            vector = item.get("embedding")
            if vector:
                vectors.append([float(value) for value in vector])
        if not vectors:
            raise RuntimeError(f"SigLIP2 server returned no embedding: {str(data)[:300]}")
        return vectors

    def _sync_dimension(self, vector: list[float]) -> None:
        if self.dimension <= 0 and vector:
            self.dimension = len(vector)


def _get_local_chinese_clip_backend(
    *,
    model_name: str | None,
    device: str | None,
    local_files_only: bool | None,
) -> LocalChineseClipBackend:
    resolved_model = _resolve_local_model_name(model_name)
    resolved_device = _resolve_local_device(device)
    resolved_local_files_only = _resolve_local_files_only(local_files_only)
    cache_key = (resolved_model, resolved_device, resolved_local_files_only)
    backend = _LOCAL_CHINESE_CLIP_BACKENDS.get(cache_key)
    if backend is None:
        backend = LocalChineseClipBackend(
            model_name=resolved_model,
            device=resolved_device,
            local_files_only=resolved_local_files_only,
        )
        _LOCAL_CHINESE_CLIP_BACKENDS[cache_key] = backend
    return backend


def _resolve_local_model_name(model_name: str | None) -> str:
    resolved = (
        model_name
        or os.getenv("CHINESE_CLIP_LOCAL_DIR")
        or os.getenv("CHINESE_CLIP_MODEL_NAME")
        or DEFAULT_CHINESE_CLIP_MODEL
    )
    if not resolved:
        raise RuntimeError("CHINESE_CLIP_MODEL_NAME or CHINESE_CLIP_LOCAL_DIR is required")
    return resolved


def _resolve_local_device(device: str | None) -> str:
    if device or os.getenv("CHINESE_CLIP_DEVICE"):
        return device or os.getenv("CHINESE_CLIP_DEVICE") or "cpu"
    try:
        import torch
        import torch_npu  # noqa: F401

        if torch.npu.is_available():
            return "npu:0"
    except ImportError:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _resolve_local_files_only(local_files_only: bool | None) -> bool:
    return _env_bool("CHINESE_CLIP_LOCAL_FILES_ONLY", False) if local_files_only is None else local_files_only


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized in {"local", "chinese_clip", "chinese-clip", "cn_clip", "cn-clip"}:
        return "chinese_clip"
    if normalized in {"siglip", "siglip2", "open_clip", "openclip"}:
        return "siglip2"
    if normalized in {"siglip_server", "siglip-server", "siglip_server_http", "http_image", "remote_image"}:
        return "siglip_server"
    if normalized in {"volcengine", "ark", "cloud", "doubao", "doubao_vision"}:
        return "volcengine"
    return normalized


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

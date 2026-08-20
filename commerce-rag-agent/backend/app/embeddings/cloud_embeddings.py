import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


class ArkEmbeddingError(RuntimeError):
    pass


class OpenAIEmbeddingClient:
    """OpenAI 兼容文本嵌入客户端（vLLM / Xinference 等自建服务）。

    配置：
    - TEXT_EMBEDDING_BASE_URL：服务地址，如 http://host:8001（自动补 /v1）或 http://host:8001/v1
    - TEXT_EMBEDDING_MODEL：模型名，如 Qwen3-Embedding-8B
    - TEXT_EMBEDDING_API_KEY：可选，内网服务免鉴权时留空
    """

    def __init__(self) -> None:
        load_dotenv()

        self.api_key = os.getenv("TEXT_EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") or ""
        self.base_url = os.getenv("TEXT_EMBEDDING_BASE_URL", "").rstrip("/")
        self.model = os.getenv("TEXT_EMBEDDING_MODEL", "").strip()
        self.timeout = int(os.getenv("TEXT_EMBEDDING_TIMEOUT_SECONDS", "60"))
        self.encoding_format = os.getenv("TEXT_EMBEDDING_ENCODING_FORMAT", "float")
        if not self.base_url:
            raise ArkEmbeddingError("Missing TEXT_EMBEDDING_BASE_URL in .env")
        if not self.model:
            raise ArkEmbeddingError("Missing TEXT_EMBEDDING_MODEL in .env")

    def embed_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must not be empty")
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self.model,
            "input": [(text or "").strip() or " " for text in texts],
            "encoding_format": self.encoding_format,
        }
        data = self._post_json(self._endpoint("embeddings"), payload)
        return self._extract_openai_embeddings(data)

    def _endpoint(self, path: str) -> str:
        # 兼容 base 带 /v1 与不带 /v1 两种写法
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/{path}"
        return f"{self.base_url}/v1/{path}"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.RequestException as error:
            raise ArkEmbeddingError(f"OpenAI embedding request failed: {error}") from error
        if response.status_code >= 400:
            raise ArkEmbeddingError(
                f"OpenAI embedding API error {response.status_code}: {response.text[:1000]}"
            )
        try:
            return response.json()
        except ValueError as error:
            raise ArkEmbeddingError(
                f"OpenAI embedding API returned non-JSON response: {response.text[:1000]}"
            ) from error

    @staticmethod
    def _extract_openai_embeddings(data: dict[str, Any]) -> list[list[float]]:
        items = data.get("data")
        if not isinstance(items, list) or not items:
            raise ArkEmbeddingError(f"Cannot find embedding vector in response: {str(data)[:1000]}")
        vectors: list[tuple[int, list[float]]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            vector = item.get("embedding")
            if vector is None or not isinstance(vector, list):
                continue
            vectors.append((int(item.get("index", len(vectors))), [float(value) for value in vector]))
        if not vectors:
            raise ArkEmbeddingError(f"Cannot find embedding vector in response: {str(data)[:1000]}")
        vectors.sort(key=lambda pair: pair[0])
        return [vector for _, vector in vectors]


class ArkEmbeddingClient:
    """Volcengine Ark multimodal embedding client."""

    def __init__(self) -> None:
        load_dotenv()

        self.api_key = (
            os.getenv("ARK_EMBEDDING_API_KEY")
            or os.getenv("ARK_API_KEY")
            or os.getenv("DOUBAO_API_KEY")
        )
        if not self.api_key:
            raise ArkEmbeddingError("Missing ARK_API_KEY or ARK_EMBEDDING_API_KEY in .env")

        self.base_url = os.getenv(
            "ARK_EMBEDDING_BASE_URL",
            "",
        ).rstrip("/")

        self.text_model = os.getenv(
            "ARK_TEXT_EMBEDDING_MODEL",
            "",
        )

        self.multimodal_model = os.getenv(
            "ARK_MULTIMODAL_EMBEDDING_MODEL",
            "",
        )
        if not self.base_url:
            raise ArkEmbeddingError("Missing ARK_EMBEDDING_BASE_URL in .env")
        if not self.text_model or not self.multimodal_model:
            raise ArkEmbeddingError("Missing ARK_TEXT_EMBEDDING_MODEL or ARK_MULTIMODAL_EMBEDDING_MODEL in .env")

        self.timeout = int(os.getenv("ARK_EMBEDDING_TIMEOUT_SECONDS", "60"))
        self.encoding_format = os.getenv("ARK_EMBEDDING_ENCODING_FORMAT", "float")

    def embed_text(self, text: str) -> list[float]:
        """
        注意：
        这里也走多模态接口，不走 /embeddings。
        因为文本和图片使用同一套多模态向量模型，具体模型由 .env 配置。
        """
        return self.embed_multimodal_text(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for text in texts:
            vectors.append(self.embed_multimodal_text(text))
        return vectors

    def embed_multimodal_text(self, text: str) -> list[float]:
        text = (text or "").strip()
        if not text:
            raise ValueError("text must not be empty")

        payload = {
            "model": self.multimodal_model,
            "input": [
                {
                    "type": "text",
                    "text": text,
                }
            ],
            "encoding_format": self.encoding_format,
        }

        data = self._post_json("/embeddings/multimodal", payload)
        return self._extract_embeddings(data)[0]

    def embed_image_path(self, path: str) -> list[float]:
        image_path = Path(path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if not image_path.is_file():
            raise ValueError(f"Image path is not a file: {path}")

        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{encoded}"

        payload = {
            "model": self.multimodal_model,
            "input": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_uri,
                    },
                }
            ],
            "encoding_format": self.encoding_format,
        }

        data = self._post_json("/embeddings/multimodal", payload)
        return self._extract_embeddings(data)[0]

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ArkEmbeddingError(f"Ark embedding request failed: {error}") from error

        if response.status_code >= 400:
            raise ArkEmbeddingError(
                f"Ark embedding API error {response.status_code}: {response.text[:1000]}"
            )

        try:
            return response.json()
        except ValueError as error:
            raise ArkEmbeddingError(
                f"Ark embedding API returned non-JSON response: {response.text[:1000]}"
            ) from error

    def _extract_embeddings(self, data: dict[str, Any]) -> list[list[float]]:
        """
        兼容几种返回格式：

        1. 火山方舟多模态：
           {"data": {"embedding": [...]}}

        2. OpenAI-compatible：
           {"data": [{"embedding": [...]}]}

        3. 其他：
           {"embedding": [...]}
           {"vectors": [[...]]}
        """

        if isinstance(data.get("data"), dict):
            inner_data = data["data"]

            vector = inner_data.get("embedding") or inner_data.get("vector")
            if vector is not None:
                if vector and isinstance(vector[0], list):
                    vector = vector[0]
                return [[float(value) for value in vector]]

            vectors = inner_data.get("embeddings") or inner_data.get("vectors")
            if isinstance(vectors, list):
                return [[float(value) for value in vector] for vector in vectors]

        if isinstance(data.get("data"), list):
            vectors = []

            for item in data["data"]:
                vector = item.get("embedding") or item.get("vector")
                if vector is None:
                    continue

                if vector and isinstance(vector[0], list):
                    vector = vector[0]

                vectors.append([float(value) for value in vector])

            if vectors:
                return vectors

        if isinstance(data.get("embedding"), list):
            vector = data["embedding"]

            if vector and isinstance(vector[0], list):
                vector = vector[0]

            return [[float(value) for value in vector]]

        if isinstance(data.get("vectors"), list):
            return [[float(value) for value in vector] for vector in data["vectors"]]

        raise ArkEmbeddingError(
            f"Cannot find embedding vector in response: {str(data)[:1000]}"
        )

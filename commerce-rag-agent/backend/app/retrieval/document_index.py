import hashlib
import json
import os
from typing import Any

from app.embeddings.bge_m3 import BgeM3Embedding


KNOWLEDGE_DOCS_COLLECTION = "knowledge_docs"


class DocumentIndex:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        embedding: BgeM3Embedding | None = None,
    ) -> None:
        self.chroma_path = chroma_path or os.getenv("CHROMA_PATH", "./app/data/chroma")
        self.embedding = embedding or BgeM3Embedding()
        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            KNOWLEDGE_DOCS_COLLECTION,
            metadata=self._create_collection_metadata(),
        )

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        self._ensure_embedding_compatible()
        documents = [chunk["text"] for chunk in chunks]
        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=documents,
            metadatas=[chunk["metadata"] for chunk in chunks],
            embeddings=self.embedding.embed_documents(documents),
        )
        self.collection.modify(metadata=self._collection_metadata())

    def rebuild_chunks(self, chunks: list[dict[str, Any]]) -> None:
        try:
            self.client.delete_collection(KNOWLEDGE_DOCS_COLLECTION)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            KNOWLEDGE_DOCS_COLLECTION,
            metadata=self._create_collection_metadata(),
        )
        if not chunks:
            return
        documents = [chunk["text"] for chunk in chunks]
        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=documents,
            metadatas=[chunk["metadata"] for chunk in chunks],
            embeddings=self.embedding.embed_documents(documents),
        )
        self.collection.modify(metadata=self._chunks_metadata(chunks))

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_query(query)],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": result["ids"][0][index],
                "text": result["documents"][0][index],
                "metadata": result["metadatas"][0][index],
                "distance": result["distances"][0][index],
            }
            for index in range(len(result["ids"][0]))
        ]

    def _ensure_embedding_compatible(self) -> None:
        try:
            metadata = self.collection.metadata or {}
            if _metadata_matches(metadata, self._embedding_metadata()):
                return
        except Exception:
            pass
        try:
            self.client.delete_collection(KNOWLEDGE_DOCS_COLLECTION)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            KNOWLEDGE_DOCS_COLLECTION,
            metadata=self._create_collection_metadata(),
        )

    def _collection_metadata(self) -> dict[str, Any]:
        return {
            "kind": "knowledge_docs",
            "source": "document_chunks",
            "chunk_count": self.collection.count(),
            **self._embedding_metadata(),
        }

    def _chunks_metadata(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "kind": "knowledge_docs",
            "source": "document_chunks",
            "chunk_count": len(chunks),
            "fingerprint": chunks_fingerprint(chunks),
            **self._embedding_metadata(),
        }

    def _create_collection_metadata(self) -> dict[str, str | int]:
        return {"hnsw:space": "cosine", **self._embedding_metadata()}

    def _embedding_metadata(self) -> dict[str, str | int]:
        signature = self.embedding.signature() if hasattr(self.embedding, "signature") else {}
        return {f"embedding_{key}": value for key, value in signature.items()}


def chunks_fingerprint(chunks: list[dict[str, Any]]) -> str:
    payload = json.dumps(chunks, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metadata_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(str(actual.get(key)) == str(value) for key, value in expected.items())

"""
Default VectorStore implementation backed by LanceDB.

LanceDB is an embedded vector database built on the Lance columnar format.
Zero network dependencies — data is stored as local files.  Suitable for
development and single-machine deployments.

One LanceDB table per *embed_model*; within a table, *kb_id* is used as a
filter key.  See vdb/README.md for the collection model and production
partition strategy.

Dependencies: ``pip install lancedb pyarrow``
"""

from __future__ import annotations

import json
import re
import uuid

import lancedb
import pyarrow as pa

from entity.chunk import Chunk
from vdb.abc import BaseVectorStore


_CONFIG_TABLE = "_table_config"


class LanceDBVectorStore(BaseVectorStore):
    """
    LanceDB-backed VectorStore — default lightweight implementation.

    Data is stored on disk at the directory specified by *uri*.  Each embedding
    model maps to a separate LanceDB table, created lazily on the first
    :meth:`add` call.
    """

    def __init__(self, uri: str) -> None:
        self._db = lancedb.connect(uri)

    # --- Helpers --- #

    @staticmethod
    def _table_name(embed_model: str) -> str:
        """Convert an embed model name into a valid LanceDB table identifier."""
        # Replace characters that are unfriendly to SQL identifiers
        sanitised = re.sub(r"[^a-zA-Z0-9_]", "_", embed_model)
        return f"emb_{sanitised}"

    def _ensure_config(self):
        """Get or create the ``_table_config`` metadata table.

        Stores ``(embed_model, vector_dim)`` pairs for validating
        dimension consistency across sessions.
        """
        try:
            return self._db.open_table(_CONFIG_TABLE)
        except Exception:
            schema = pa.schema([
                pa.field("embed_model", pa.string()),
                pa.field("vector_dim", pa.int32()),
            ])
            return self._db.create_table(_CONFIG_TABLE, schema=schema)

    def _open_table(self, embed_model: str):
        """Return the LanceDB table for *embed_model*, or None if it doesn't exist."""
        try:
            return self._db.open_table(self._table_name(embed_model))
        except Exception:
            return None

    def _ensure_table(self, embed_model: str, vector_dim: int):
        """Get or create the LanceDB table for *embed_model*.

        On first access the vector table is created and its dimension is
        recorded in ``_table_config``.  Subsequent calls validate that
        *vector_dim* matches the registered dimension.
        """
        config = self._ensure_config()

        # Ensure vector_dim matches with defined embed_model
        for row in config.to_arrow().to_pylist():
            if row["embed_model"] == embed_model:
                if row["vector_dim"] != vector_dim:
                    raise ValueError(
                        f"Dimension mismatch for embed_model '{embed_model}': "
                        f"expected {row['vector_dim']}, got {vector_dim}"
                    )
                return self._open_table(embed_model)

        # First use — create the vector table, then register it
        schema = pa.schema([
            # Redundant PK
            pa.field("chunk_id", pa.string()),

            # Actual PK (kb -> doc -> chunk_index)
            pa.field("kb_id", pa.int64()),
            pa.field("doc_id", pa.int64()),
            pa.field("index", pa.int32()),

            pa.field("content", pa.string()),
            pa.field("metadata", pa.string()),           # JSON-serialised dict

            pa.field("vector", pa.list_(pa.float32(), vector_dim)),
        ])

        table = self._db.create_table(self._table_name(embed_model), schema=schema)
        config.add([{"embed_model": embed_model, "vector_dim": vector_dim}])
        return table

    # --- Internal: entity ↔ record --- #

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique chunk identifier.

        LanceDB has no SQL-style AUTOINCREMENT — IDs are managed internally
        by this implementation.  UUID4 hex is used for its simplicity and
        zero coordination overhead.
        """
        return uuid.uuid4().hex

    @staticmethod
    def _to_record(chunk: Chunk, vector: list[float], chunk_id: str) -> dict:
        """Wrap *chunk* and *vector* into a LanceDB-compatible record dict.

        This is the boundary between the public :class:`Chunk` entity and the
        internal storage format.
        """
        return {
            "chunk_id": chunk_id,
            "kb_id": chunk.kb_id,
            "doc_id": chunk.doc_id,
            "index": chunk.index,
            "content": chunk.content,
            "metadata": json.dumps(chunk.metadata) if chunk.metadata else None,
            "vector": vector,
        }

    @staticmethod
    def _record_to_chunk(record: dict, kb_id: int) -> Chunk:
        """Convert a LanceDB result record back into a :class:`Chunk`."""
        meta_raw = record.get("metadata")
        return Chunk(
            chunk_id=record["chunk_id"],
            doc_id=record["doc_id"],
            kb_id=kb_id,
            index=record["index"],
            content=record["content"],
            metadata=json.loads(meta_raw) if meta_raw else None,
        )

    # --- Write --- #

    def add(
        self, embed_model: str, chunks: list[Chunk], vectors: list[list[float]],
    ) -> list[str]:
        """
        Insert chunks into lancedb
        """

        if len(chunks) != len(vectors):
            raise ValueError(
                f"Length mismatch: {len(chunks)} chunks vs {len(vectors)} vectors"
            )
        if not chunks:
            return []

        vector_dim = len(vectors[0])
        table = self._ensure_table(embed_model, vector_dim)

        chunk_ids: list[str] = []
        records: list[dict] = []
        for chunk, vector in zip(chunks, vectors):
            cid = self._generate_id()
            chunk_ids.append(cid)
            records.append(self._to_record(chunk, vector, cid))

        table.add(records)
        return chunk_ids

    # --- Read --- #

    def search(
        self,
        embed_model: str,
        kb_id: int,
        query_vector: list[float],
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        table = self._open_table(embed_model)
        if table is None:
            return []

        results = (
            table.search(query_vector)
            .where(f"kb_id = {kb_id}")
            .limit(top_k)
            .distance_type("cosine")
            .to_list()
        )
        return [
            (self._record_to_chunk(r, kb_id), r["_distance"])
            for r in results
        ]

    # --- Delete --- #

    def delete(
        self, embed_model: str, kb_id: int, chunk_ids: list[str],
    ) -> None:
        if not chunk_ids:
            return
        table = self._open_table(embed_model)
        if table is None:
            return
        # chunk_ids are UUID hex — safe to inline into SQL predicate
        ids_literal = ", ".join(f"'{cid}'" for cid in chunk_ids)
        table.delete(f"kb_id = {kb_id} AND chunk_id IN ({ids_literal})")

    def delete_by_document(
        self, embed_model: str, kb_id: int, doc_id: int,
    ) -> None:
        table = self._open_table(embed_model)
        if table is None:
            return
        table.delete(f"kb_id = {kb_id} AND doc_id = {doc_id}")

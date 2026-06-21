"""
VDB contracts.

The Vector Database stores document chunks and their embedding vectors, providing
semantic (similarity-based) retrieval. This feature is a pure storage + search
layer — embedding computation is an external concern handled by the caller.

**Collection model**: collections are keyed by *embed_model*. All knowledge bases
using the same embedding model share a single vector collection. Within each
collection, *kb_id* acts as a logical partition key — production implementations
should partition on this key to keep table sizes manageable.

Default implementation is a lightweight LanceDB-backed store. Production
deployments should inject a real vector database (Milvus, Pinecone, etc.)
with native partitioning support via configuration.

Chunks are NOT persisted in RDBMS; only aggregate metadata (segment_count,
embedding_status) is tracked in kb_document.
"""

from abc import ABC, abstractmethod

from entity.chunk import Chunk


class BaseVectorStore(ABC):
    """Storage and similarity-search contract for document chunks.

    Collections are keyed by ``embed_model`` (e.g. ``'text-embedding-3-small'``).
    Within a collection, ``kb_id`` acts as a logical partition boundary — every
    operation scopes to both.

    The caller is responsible for:
      - Splitting documents into chunks
      - Computing embedding vectors (using the model declared in kb_info)
      - Calling :meth:`add` to persist chunks + vectors
      - Calling :meth:`mark_embedded` on the Repository once all chunks are stored

    .. note::

        ``chunk_id`` values are assigned by the VDB implementation on
        :meth:`add`. Callers should not generate them.
    """

    # --- Write --- #

    @abstractmethod
    def add(
        self, embed_model: str, chunks: list[Chunk], vectors: list[list[float]],
    ) -> list[str]:
        """Store chunks with their embedding vectors.

        Each chunk is paired positionally with one vector. The VDB
        implementation assigns a unique ``chunk_id`` to each stored chunk.

        :param embed_model:  embedding model name (determines the target
                             collection; e.g. ``'text-embedding-3-small'``)
        :param chunks:       chunks to store (``kb_id`` and ``doc_id`` must
                             be set; all chunks must target the same *kb_id*)
        :param vectors:      embedding vectors, one per chunk (each vector
                             length must match the model's ``embed_dim``)
        :returns:            ``chunk_id`` values assigned to the stored chunks,
                             in the same order as *chunks*
        :raises ValueError:  if ``len(chunks) != len(vectors)``
        """
        ...

    # --- Read --- #

    @abstractmethod
    def search(
        self,
        embed_model: str,
        kb_id: int,
        query_vector: list[float],
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """Semantic similarity search within a knowledge base.

        Only chunks belonging to *kb_id* are considered.

        :param embed_model:  embedding model name (determines the target
                             collection)
        :param kb_id:        target knowledge base (logical partition)
        :param query_vector: embedding vector of the query text
        :param top_k:        maximum number of results to return
        :returns:            ordered list of ``(chunk, score)`` pairs,
                             best match first. Returns an empty list when
                             the KB contains no chunks.
        """
        ...

    # --- Delete --- #

    @abstractmethod
    def delete(
        self, embed_model: str, kb_id: int, chunk_ids: list[str],
    ) -> None:
        """Delete specific chunks by id.

        Idempotent — deleting a non-existent chunk is a no-op.

        :param embed_model: embedding model name (determines the target
                            collection)
        :param kb_id:       target knowledge base (logical partition)
        :param chunk_ids:   chunk identifiers to remove
        """
        ...

    @abstractmethod
    def delete_by_document(
        self, embed_model: str, kb_id: int, doc_id: int,
    ) -> None:
        """Delete all chunks belonging to a document.

        Idempotent — deleting chunks for a document that has no chunks is a
        no-op. Useful for re-indexing workflows where a document is
        re-segmented and old chunks must be replaced.

        :param embed_model: embedding model name (determines the target
                            collection)
        :param kb_id:       target knowledge base (logical partition)
        :param doc_id:      document whose chunks should be removed
        """
        ...

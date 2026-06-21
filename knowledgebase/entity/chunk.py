from dataclasses import dataclass


@dataclass
class Chunk:
    """
    A segment of a document, stored in the Vector Database for semantic retrieval.

    Chunks are NOT persisted in RDBMS; they live in the VDB. The RDBMS only
    tracks aggregate counts via kb_document.segment_count and
    kb_document.embedding_status.
    """

    chunk_id: str       # Unique chunk identifier (assigned by VDB)
    doc_id: int         # Parent document id
    kb_id: int          # Parent knowledge base id
    index: int          # Position within the document (0-based)
    content: str        # Text content of this chunk

    # Extensible metadata — callers can attach domain-specific info such as
    # page number (PDF), line range (code), token count, etc.
    metadata: dict | None = None

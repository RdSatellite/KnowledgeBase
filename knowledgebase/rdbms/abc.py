"""
RDBMS contracts.

We use RDBMS to store document's metadata, carrying business logic. You can read 
rdbms/README.md to catch the core idea.

Default implementation based on sqlite, but we recommend you use MySQL 8.0+ in Production.

Those design is not enabled by default:
    - Soft deletion
    - DB Partition
"""

from abc import ABC, abstractmethod
from typing import Optional

from entity.document import Document


# --- RDBMS Scope Entities --- #

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class KbConfig:
    """Read-only view of a kb_info row."""

    kb_id: int
    kb_name: str
    owner_uid: int

    # Fixed configuration
    embed_model: str
    embed_dim: int
    ext_config: dict | None = None # Used for extra configurations, this should be handled by other component

    # Timestamps (managed by the persistence layer)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # NOTE: status field exists in the schema for future soft-delete support
    # NOTE: but is not surfaced in the default ABC — see module docstring.


class Repository(ABC):
    """
    Persistence contract for knowledge base metadata and documents.

    Manages two logical tables:
      - kb_info      — knowledge base scope configurations
      - kb_document  — document metadata (scoped within a knowledge base)

    All document operations are scoped by ``(kb_id, doc_id)`` — kb_id acts as
    a tenant boundary enforced by the UNIQUE KEY uk_kb_doc (kb_id, id).

    .. note::

        The kb_info.status column (0=disabled, 1=enabled) exists in the schema
        but soft-delete / disable-enable methods are intentionally absent from
        this ABC.
    """

    # --- Knowledge Base --- # 

    @abstractmethod
    def create_kb(
        self,
        owner_uid: int,
        kb_name: str,
        embed_model: str,
        embed_dim: int,
        ext_config: Optional[dict] = None,
    ) -> int:
        """
        Create a new knowledge base record.

        NOTE: UNIQUE KEY (owner_uid, kb_name)
        NOTE: This means user cannot create databases sharing the same name 
        :param owner_uid:   owner / tenant identifier
        :param kb_name:     human-readable name (must be unique per owner)
        
        NOTE: --- About Embedding ---
        NOTE: Embedding info is usually depend on providers, you should check both model and dim carefully
        NOTE: Mismatch will introduce hidden performancce loss
        
        NOTE: Updating embed configurations is not allowed, this will cause full-table update
        NOTE: At least, in infra-level we force you to delete the kb and create it with your new embed

        :param embed_model: embedding model name (e.g. 'text-embedding-3-small')
        :param embed_dim:   vector dimension produced by the model
        :param ext_config:  optional extensible parameters (stored as JSON)
        
        :return:            kb_id of the newly created record
        :raises ValueError: if (owner_uid, kb_name) already exists
        """
        ...

    @abstractmethod
    def get_kb(self, kb_id: int) -> KbConfig:
        """
        Retrieve a knowledge base configuration.

        :raises LookupError: if kb_id does not exist
        """
        ...

    @abstractmethod
    def list_kb_by_owner(self, owner_uid: int) -> list[KbConfig]:
        """
        List all knowledge bases owned by *owner_uid*.
        """
        ...

    @abstractmethod
    def update_kb(
        self,
        kb_id: int,
        *,
        kb_name: str | None = None,
        ext_config: dict | None = None,
    ) -> None:
        """
        Update mutable fields of a knowledge base.

        Only the fields explicitly passed (non-None) are updated.

        :raises LookupError: if kb_id does not exist
        :raises ValueError:  if the new kb_name conflicts with an existing one
                              under the same owner
        """
        ...

    # TODO: remove_kb(kb_id) — physical delete.

    # --- Documents --- #

    @abstractmethod
    def add_document(
        self,
        kb_id: int,
        title: str,
        mime_type: str,
        uri: str,
        content_hash: str,
        *,
        security_level: Optional[int] = None,
    ) -> int:
        """
        Register a document in a knowledge base.

        Called **after** the original file has been stored via OSS — *uri*
        references the stored object.

        :param kb_id:          target knowledge base
        :param title:          document title
        :param mime_type:      file type (e.g. 'pdf', 'md', 'docx')
        :param uri:            OSS URI pointing to the stored original
        :param content_hash:   SHA-256 hash for dedup

        :param security_level: (Optional) security classification
        
        :return:               doc_id of the new record
        :raises LookupError:   if kb_id does not exist
        """
        ...

    @abstractmethod
    def get_document(self, kb_id: int, doc_id: int) -> Document:
        """
        Retrieve a single document by its (kb_id, doc_id) pair.

        :raises LookupError: if not found
        """
        ...

    @abstractmethod
    def list_documents(self, kb_id: int) -> list[Document]:
        """
        List all documents in a knowledge base.
        """
        ...

    @abstractmethod
    def update_document(
        self,
        kb_id: int,
        doc_id: int,
        *,
        title: Optional[str] = None,
        security_level: Optional[int] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        """
        Update mutable document metadata.

        Only the fields explicitly passed (non-None) are updated.

        :raises LookupError: if the (kb_id, doc_id) pair does not exist
        """
        ...

    @abstractmethod
    def remove_document(self, kb_id: int, doc_id: int) -> None:
        """
        Physically delete a document record.

        :raises LookupError: if not found
        """
        ...

    @abstractmethod
    def mark_embedded(self, kb_id: int, doc_id: int, segment_count: int) -> None:
        """
        Mark a document as vectorized.

        Sets ``embedding_status = 1`` and records the final segment count.
        Called by the embedding pipeline after all chunks have been stored
        in the VDB.

        TODO: We will support more state (preprocessed, chunked, vectorized, etc.) in the future

        :raises LookupError: if not found
        """
        ...

"""
EmbedFunction contract.

EmbedFunction converts text into dense vectors (embeddings). Each instance is
bound to a specific model and produces vectors of a fixed dimension.

This is a standalone infra feature — it is NOT coupled to any storage layer.
Components that need text-to-vector conversion (OSS for projection pipelines,
VDB for query embedding, etc.) can depend on this contract independently.
"""

from abc import ABC, abstractmethod


class BaseEmbedFunction(ABC):
    """Convert text into embedding vectors using a specific model.

    Each implementation is bound to a particular model (e.g.
    ``text-embedding-3-small``) and declares its output dimension.  Callers
    should validate that ``model`` / ``dim`` match the target ``kb_info``
    before use.
    """

    # --- Model identity --- #

    @property
    @abstractmethod
    def model(self) -> str:
        """Embedding model name (e.g. ``'text-embedding-3-small'``)."""
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        """Dimensionality of the vectors produced by this model."""
        ...

    # --- Embedding --- #

    def __call__(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts)

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert *texts* into embedding vectors.

        :param texts:  one or more text strings to embed
        :returns:      embedding vectors in the same order as *texts*;
                       each vector has length :attr:`dim`
        """
        ...

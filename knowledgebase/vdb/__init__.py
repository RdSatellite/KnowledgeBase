from .abc import BaseVectorStore

# Default implementation
from .impls.lancedb import LanceDBVectorStore

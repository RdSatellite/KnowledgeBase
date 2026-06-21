import uuid
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, override

from ..abc import BaseObjectStore

class LocalObjectStore(BaseObjectStore):
    """
    Local ObjectStore implementation.

    URI: file://{file_path}
    """

    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # --- Helpers --- #

    PREFIX = "file://"
    def _uri_to_path(self, uri: str) -> Path:
        """Resolve URI, transfer to local path"""
        if not uri.startswith(self.PREFIX):
            raise ValueError(f"Unsupported URI scheme: {uri}")
        
        return Path(uri[len(self.PREFIX):])

    def _path_to_uri(self, path: Path) -> str:
        return self.PREFIX + str(path)

    # --- Impls --- #

    @override
    def put(self, data: BinaryIO) -> str:
        filename = uuid.uuid4().hex

        dst = self._root / filename
        dst.write_bytes(data.read())
        
        return self._path_to_uri(dst)

    @override
    def get(self, uri: str) -> BinaryIO:
        path = self._uri_to_path(uri)
        if not path.exists():
            raise RuntimeError(f"Object does not exist: {uri}")
        
        content = path.read_bytes()
        return BytesIO(content)

    @override
    def delete(self, uri: str) -> None:
        target = self._uri_to_path(uri)
        if not target.exists():
            raise RuntimeError(f"Object does not exist or has been removed: {uri}")
        
        target.unlink()

"""
Example: LocalObjectStore for OSS component
"""

import sys
import tempfile
from io import BytesIO
from pathlib import Path

# Ensure import
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from knowledgebase.oss.impls.local import LocalObjectStore


# The root dir is example/data/
STORE_DIR = _project_root/"examples"/"data"
STORE_DIR.mkdir(parents=True, exist_ok=True)


# 1. Create LocalObjectStore
store = LocalObjectStore(STORE_DIR)
print(f"Store created at : {STORE_DIR}")


# 2. Read file under examples/assets
FILE_PATH = _project_root/"examples"/"assets"/"hello.md"

with open(FILE_PATH, "rb") as f:
    # 3. Store the file
    # ObjectStore.put() receives BinaryIO, returns URI
    uri = store.put(f)
    print(f"The generated URI is {uri}")

# 4. Get the file back
# ObjectStore.get() receives URI, and return BinaryIO
with store.get(uri) as stream:
    read_back = stream.read()
    print(f"Read {len(read_back)} bytes")
    print(f"Content: {read_back!r}")

# 5. Delete the object
store.delete(uri)
print(f"Object storage: {uri} deleted.")

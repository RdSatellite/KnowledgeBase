"""
Example: SqliteRepository for RDBMS component
"""

import sys
from pathlib import Path

# Ensure import
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "knowledgebase"))

from knowledgebase.rdbms.impls.sqlite import SqliteRepository

# 1. Create repository
DB_PATH = _project_root / "examples" / "data" / "rdbms.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Remove stale db so each run starts fresh
if DB_PATH.exists():
    DB_PATH.unlink()

repo = SqliteRepository(str(DB_PATH))
print(f"Repository created, backing store: {DB_PATH}\n")


# 2. Create KB
# You can use Repository.create_kb() to create a knowledge base
print("─── create_kb ───")

kb_id_a = repo.create_kb(
    owner_uid=1001,
    kb_name="Research Papers",
    embed_model="text-embedding-3-small",
    embed_dim=1536,
    ext_config={"lang": "en", "domain": "cs"},
)
print(f"Created kb A (id={kb_id_a}): Research Papers")

kb_id_b = repo.create_kb(
    owner_uid=1001,
    kb_name="Meeting Notes",
    embed_model="text-embedding-3-large",
    embed_dim=3072,
)
print(f"Created kb B (id={kb_id_b}): Meeting Notes (no ext_config)\n")

# NOTE: In our RDBMS, there exists a uk: (owner_uid, kb_name)
# NOTE: which means you shouldn't create dbs with duplicated names.
try:
    repo.create_kb(owner_uid=1001, kb_name="Research Papers", embed_model="m", embed_dim=128)
    print("ERROR: should have raised for duplicate name")
except Exception as e:
    print(f"Duplicate name correctly rejected: {type(e).__name__}\n")


# 3. Get kb metadata
# You can get kb metadata via Repository.get_kb()
print("─── get_kb ───")

kb_a = repo.get_kb(kb_id_a)
print(f"Retrieved kb A: name={kb_a.kb_name!r}, model={kb_a.embed_model!r}, "
      f"dim={kb_a.embed_dim}, ext_config={kb_a.ext_config}")


# 4. List kbs by owner
# You can list all kbs belong to an owner via Repository.list_kb_by_owner()
# This is useful for multi-db retrieval
print("─── list_kb_by_owner ───")

kbs = repo.list_kb_by_owner(1001)
print(f"Owner 1001 has {len(kbs)} kb(s): {[k.kb_name for k in kbs]}")

empty = repo.list_kb_by_owner(9999)
print(f"Owner 9999 has {len(empty)} kb(s)\n")


# 5. Update kb
# You can update kb's metadata via Repository.update_kb()
print("─── update_kb ───")

repo.update_kb(kb_id_a, kb_name="Research Papers v2")
print(f"Renamed kb A: {repo.get_kb(kb_id_a).kb_name!r}")

repo.update_kb(kb_id_a, ext_config={"lang": "zh", "domain": "ai"})
print(f"Updated ext_config: {repo.get_kb(kb_id_a).ext_config}")


# 6. Add document
# You can add document via Repository.add_document()
# WARNING: This will trigger OSS, VectorDB logic. And should be called by scheduler.
print("─── add_document ───")

doc_id_1 = repo.add_document(
    kb_id=kb_id_a,
    title="Attention Is All You Need",
    mime_type="pdf",
    uri="file:///oss/papers/attention.pdf",
    content_hash="sha256:aaa111",
    security_level=0,
)
print(f"Added doc 1 (id={doc_id_1}): Attention Is All You Need")

doc_id_2 = repo.add_document(
    kb_id=kb_id_a,
    title="BERT: Pre-training of Deep Bidirectional Transformers",
    mime_type="pdf",
    uri="file:///oss/papers/bert.pdf",
    content_hash="sha256:bbb222",
    security_level=2,
)
print(f"Added doc 2 (id={doc_id_2}): BERT")

doc_id_3 = repo.add_document(
    kb_id=kb_id_b,
    title="Weekly Sync — 2026W25",
    mime_type="md",
    uri="file:///oss/meetings/2026w25.md",
    content_hash="sha256:ccc333",
)
print(f"Added doc 3 (id={doc_id_3}): Weekly Sync (different kb)\n")


# 7. Get document
# You can get a single document via Repository.get_document()
# NOTE: We use (kb_id, doc_id) to identify a document, which means you should pass both of them.
print("─── get_document ───")

doc = repo.get_document(kb_id_a, doc_id_1)
print(f"Retrieved doc: title={doc.title!r}, mime={doc.mime_type!r}, "
      f"uri={doc.uri!r}, security_level={doc.security_level}")

try:
    repo.get_document(kb_id_a, 99999)
    print("ERROR: should have raised LookupError")
except LookupError as e:
    print(f"Missing doc correctly rejected: {e}\n")


# 8. List documents
# You can list all documents in kb via Repository.list_documents()
print("─── list_documents ───")

docs_a = repo.list_documents(kb_id_a)
print(f"kb A has {len(docs_a)} doc(s): {[d.title for d in docs_a]}")

docs_b = repo.list_documents(kb_id_b)
print(f"kb B has {len(docs_b)} doc(s): {[d.title for d in docs_b]}\n")


# 9. Update document's metadata
# You can update document's info by Repository.update_document()
print("─── update_document ───")

repo.update_document(kb_id_a, doc_id_1, title="Attention Is All You Need (2017)")
print(f"Renamed doc 1: {repo.get_document(kb_id_a, doc_id_1).title!r}")

# WARNING: You shouldn't update content_hash without the source truth in OSS modified.
repo.update_document(kb_id_a, doc_id_1, security_level=1, content_hash="sha256:newhash")
doc_updated = repo.get_document(kb_id_a, doc_id_1)
print(f"Updated security_level={doc_updated.security_level} "
      f"(content_hash is RDBMS-internal, not surfaced on Document entity)")


# 10. Update state
# You can update the state by repo.mark_embedded
# TODO: maybe not only embedded, will be updated in the future when scheduler is done. At that time we know
# TODO: how many stages we will go through.
print("─── mark_embedded ───")

repo.mark_embedded(kb_id_a, doc_id_1, segment_count=42)
print(f"Marked doc 1 as embedded with 42 segments")


# 11. Remove document
# You can remove document info via Repository.remove_document()
# WARNING: Removing document's info should trigger deletion in OSS and VectorDB, which should be called by scheduler
print("─── remove_document ───")

repo.remove_document(kb_id_a, doc_id_2)
print(f"Removed doc 2 (BERT) — kb A now has {len(repo.list_documents(kb_id_a))} doc(s)")

try:
    repo.remove_document(kb_id_a, 99999)
    print("ERROR: should have raised LookupError")
except LookupError as e:
    print(f"Remove missing doc correctly rejected: {e}\n")

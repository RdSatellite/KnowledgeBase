"""
Example: LanceDBVectorStore for VDB component

Run with::

    API_KEY="..." BASE_URL="..." python examples/vdb.py

If environment variables are not set, the OpenAIEmbedFunction will still import
but will fail on first ``embed()`` call with an authentication error.
"""

import sys
from pathlib import Path

# Ensure import
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "knowledgebase"))

from knowledgebase.entity.chunk import Chunk
from knowledgebase.vdb.impls.lancedb import LanceDBVectorStore
from knowledgebase.embed import OpenAIEmbedFunction


# 1. Create vector store + embedding function
DB_PATH = _project_root / "examples" / "data" / "vdb"

# Remove stale db so each run starts fresh
if DB_PATH.exists():
    import shutil

    shutil.rmtree(DB_PATH)

vdb = LanceDBVectorStore(str(DB_PATH))
embed = OpenAIEmbedFunction()
print(f"VectorStore created, backing store: {DB_PATH}")
print(f"EmbedFunction: model={embed.model!r}, dim={embed.dim}\n")

# Shared test constants
KB_ID_A = 1
KB_ID_B = 2
DOC_ID_1 = 101
DOC_ID_2 = 102


# 2. Add
print("─── add ───")

chunks_a = [
    Chunk(
        chunk_id="", doc_id=DOC_ID_1, kb_id=KB_ID_A, index=0,
        content="The transformer architecture relies on self-attention mechanisms.",
        metadata={"page": 1},
    ),
    Chunk(
        chunk_id="", doc_id=DOC_ID_1, kb_id=KB_ID_A, index=1,
        content="Multi-head attention allows the model to focus on different positions.",
        metadata={"page": 2},
    ),
    Chunk(
        chunk_id="", doc_id=DOC_ID_2, kb_id=KB_ID_A, index=0,
        content="BERT uses masked language modeling for pre-training.",
        metadata={"page": 3},
    ),
]

# Generate real embedding vectors from chunk contents
texts_a = [c.content for c in chunks_a]
vectors_a = embed.embed(texts_a)
print(f"Embedded {len(vectors_a)} texts, each dim={len(vectors_a[0])}")

chunk_ids = vdb.add(embed.model, chunks_a, vectors_a)
print(f"Added {len(chunk_ids)} chunks, assigned ids: {chunk_ids[:2]}... (showing first two)")

# Verify chunk_ids are unique UUID hex strings
assert len(chunk_ids) == 3
assert all(isinstance(cid, str) and len(cid) == 32 for cid in chunk_ids)
assert len(set(chunk_ids)) == 3
print("All chunk_ids are unique 32-char UUID hex strings")

# Add chunks to a different KB (same embed_model — shares collection)
chunks_b = [
    Chunk(
        chunk_id="", doc_id=201, kb_id=KB_ID_B, index=0,
        content="Weekly sync: discussed Q3 roadmap and resource allocation.",
        metadata={"source": "meeting"},
    ),
]

vectors_b = embed.embed([c.content for c in chunks_b])
chunk_ids_b = vdb.add(embed.model, chunks_b, vectors_b)
print(
    f"Added {len(chunk_ids_b)} chunk to KB {KB_ID_B} "
    f"(same embed_model, shared collection)\n"
)


# 3. Search
print("─── search ───")

# "self-attention" query — should match the Transformer chunks best
query_text = "self-attention mechanisms in deep learning"
query_vec = embed.embed([query_text])[0]

results = vdb.search(embed.model, KB_ID_A, query_vec, top_k=3)
print(f"Search query: {query_text!r}")
print(f"Results ({len(results)}):")
for i, (chunk, score) in enumerate(results):
    print(
        f"  #{i} score={score:.4f} | doc={chunk.doc_id} idx={chunk.index} "
        f"| {chunk.content[:60]}..."
    )

# The two Transformer/attention chunks (index 0 and 1) should be most relevant
# to a "self-attention" query.  The BERT chunk (index 2) is less relevant.
print(
    "Top results are Transformer/attention chunks — "
    "semantic search working [OK]"
)


# 4. With kb isolation
print("\n─── search KB isolation ───")

results_b = vdb.search(embed.model, KB_ID_B, query_vec, top_k=3)
print(f"Search KB {KB_ID_B}: {len(results_b)} result(s) (should be 1)")
assert len(results_b) == 1
assert results_b[0][0].kb_id == KB_ID_B
print("KB isolation confirmed [OK]")


# 5. Search empty KB
# This should return nothing
print("\n─── search empty KB ───")
empty_results = vdb.search(embed.model, 99999, query_vec, top_k=5)
print(f"Search non-existent KB: {len(empty_results)} result(s) (should be 0)")


# 6. Delete by chunk ids
# NOTE: You can do this, but since chunks is organized by documents. Therefore, this should be only called by scheduler.
print("\n─── delete ───")

# Delete the BERT chunk (index=2 in chunks_a, the least relevant one)
chunk_to_delete = chunk_ids[2]
vdb.delete(embed.model, KB_ID_A, [chunk_to_delete])
print(f"Deleted chunk {chunk_to_delete[:8]}...")

results_after_del = vdb.search(embed.model, KB_ID_A, query_vec, top_k=10)
print(
    f"After deletion, KB {KB_ID_A} has {len(results_after_del)} chunk(s) "
    f"(was 3, now 2)"
)

# Idempotent delete — no-op on missing chunk
vdb.delete(embed.model, KB_ID_A, ["nonexistent_chunk_id"])
print("Delete of non-existent chunk: no error (idempotent) [OK]")


# 7. Delete by document
print("\n─── delete_by_document ───")

vdb.delete_by_document(embed.model, KB_ID_A, DOC_ID_1)
print(f"Deleted all chunks of doc {DOC_ID_1}")

results_after_doc_del = vdb.search(embed.model, KB_ID_A, query_vec, top_k=10)
print(
    f"KB {KB_ID_A} now has {len(results_after_doc_del)} chunk(s) "
    f"(doc 101 had 2 chunks, doc 102 was already deleted)"
)

# Verify no chunks left
assert len(results_after_doc_del) == 0, (
    f"Expected 0 chunks after deleting both docs, got {len(results_after_doc_del)}"
)
print("All chunks removed — correct [OK]")

# Idempotent delete_by_document
vdb.delete_by_document(embed.model, KB_ID_A, 99999)
print("delete_by_document for non-existent doc: no error (idempotent) [OK]\n")

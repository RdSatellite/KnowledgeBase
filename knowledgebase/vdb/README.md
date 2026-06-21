# VDB — Vector Database

向量库抽象，存储文档分片（chunk）及其 embedding 向量，提供语义相似度检索。

## Collection Model

- 集合按 **embed_model** 建表（如 `text-embedding-3-small`），同名模型的所有知识库共享同一张向量表
- 表内 **kb_id** 作为逻辑分区键，所有操作同时限定 `embed_model` + `kb_id`
- `chunk_id` 由 VDB 实现分配（调用方不应自行生成）

## Table Schema

### Vector tables (`emb_{embed_model}`)

每张表（对应一个 `embed_model`）的列定义：

| Column | Type | Role |
|--------|------|------|
| `chunk_id` | `string` | Unique chunk identifier (UUID hex, assigned by VDB) |
| `kb_id` | `int64` | Knowledge base partition key |
| `doc_id` | `int64` | Parent document |
| `index` | `int32` | Position within the document (0-based) |
| `content` | `string` | Chunk text content |
| `metadata` | `string` | Extensible metadata (JSON-serialised dict, nullable) |
| `vector` | `list<float32>` | Embedding vector (fixed length = `embed_dim`) |

**Actual primary key**: `(kb_id, doc_id, index)` — identifies a chunk's logical position. `chunk_id` is a redundant unique key for single-chunk operations (delete).

### Metadata table (`_table_config`)

非向量表，记录已创建的 embed_model 及其向量维度，用于跨会话校验：

| Column | Type | Role |
|--------|------|------|
| `embed_model` | `string` | Embedding model name (as passed by caller) |
| `vector_dim` | `int32` | Vector dimension registered at table creation |

`_ensure_table` 时先查此表：已存在且维度不匹配 → `ValueError`；不存在 → 建向量表后写入记录。

## Default Implementation

`LanceDBVectorStore` — 基于 LanceDB 的嵌入式向量库，零网络依赖，数据存为本地文件。

默认实现使用 `WHERE kb_id = ...` 过滤来模拟分区隔离，适合开发环境。生产环境应注入支持原生分区的向量数据库。

## Production Partition Strategy

向量数据库在单表跨大量知识库时，索引大小会持续增长。生产环境应启用 **kb_id 原生分区** 控制索引规模：

### Milvus

```python
# 创建索引
collection.create_index(
    field_name="vector",
    index_type="IVF_FLAT",
    nlist=1024,
)

# 按 kb_id 显式创建分区
partition_name = f"kb_{kb_id}"
collection.create_partition(partition_name)
```

### Pinecone

```python
# namespace 天然隔离 kb_id
index.upsert(vectors, namespace=f"kb_{kb_id}")
```

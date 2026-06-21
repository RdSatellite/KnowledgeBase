# RDBMS — Relational Database

关系型数据库，管理知识库配置（kb_info）与文档元数据（kb_document）。

## Core Idea

RDBMS 承载业务逻辑相关的结构化元数据，不存储文档原始内容（由 OSS 管理）和向量（由 VDB 管理）。Chunk 不在 RDBMS 中建表——RDBMS 仅通过 `kb_document.segment_count` 和 `kb_document.embedding_status` 追踪聚合状态。

## Table Schema

### kb_info — Knowledge Base Scope Configurations

| Column | Type (MySQL) | Type (SQLite) | Role |
|--------|-------------|---------------|------|
| `kb_id` | `BIGINT PK` | `INTEGER PK` | Knowledge base unique ID |
| `kb_name` | `VARCHAR(256)` | `TEXT` | Human-readable name |
| `owner_uid` | `BIGINT` | `INTEGER` | Owner / tenant identifier |
| `status` | `TINYINT` | `INTEGER` | 0=disabled, 1=enabled (default 1) |
| `embed_model` | `VARCHAR(256)` | `TEXT` | Embedding model name (**immutable**) |
| `embed_dim` | `INT` | `INTEGER` | Vector dimension (**immutable**) |
| `ext_config` | `JSON` | `TEXT` | Extensible parameters (JSON) |
| `created_at` | `DATETIME` | `TEXT` | Creation timestamp |
| `updated_at` | `DATETIME` | `TEXT` | Last-update timestamp |

**Indexes**: `idx_owner (owner_uid)`, `UNIQUE uk_kb_name_owner (owner_uid, kb_name)`

> **Note**: `embed_model` and `embed_dim` are fixed at creation time. Updating them would require re-embedding all documents — the ABC does not expose an update path for these columns.

### kb_document — Document Metadata

| Column | Type (MySQL) | Type (SQLite) | Role |
|--------|-------------|---------------|------|
| `id` | `BIGINT AUTO_INCREMENT PK` | `INTEGER PK AUTOINCREMENT` | Global document ID |
| `kb_id` | `BIGINT` | `INTEGER` | FK → `kb_info.kb_id` (logical) |
| `title` | `VARCHAR(512)` | `TEXT` | Document title |
| `mime_type` | `VARCHAR(256)` | `TEXT` | File type (pdf, md, docx, …) |
| `security_level` | `TINYINT` | `INTEGER` | Security classification (nullable) |
| `content_hash` | `CHAR(64)` | `TEXT` | SHA-256 hash for dedup |
| `uri` | `VARCHAR(256)` | `TEXT` | OSS URI — original file reference |
| `segment_count` | `INT` | `INTEGER` | Number of chunks (default 0) |
| `embedding_status` | `TINYINT` | `INTEGER` | 0=unfinished, 1=completed (default 0) |
| `created_at` | `DATETIME` | `TEXT` | Creation timestamp |
| `updated_at` | `DATETIME` | `TEXT` | Last-update timestamp |

**Indexes**: `UNIQUE uk_kb_doc (kb_id, id)`, `INDEX idx_kb (kb_id)`

> **SQLite notes**: No `BIGINT`/`TINYINT` → `INTEGER`; no `JSON` → `TEXT`; `ON UPDATE CURRENT_TIMESTAMP` simulated via triggers (see `ddl/sqlite.sql`).

## Default Implementation

`SqliteRepository` — 基于 SQLite 3 的默认实现，零外部依赖，适合开发与单机部署。生产环境应注入 MySQL 8.0+ 适配器。

## Design Decisions Not Enabled by Default

以下设计已预留但**未在默认 ABC 中启用**：

### Soft Deletion

`kb_info.status` 列已定义（0=禁用, 1=启用），但 ABC 未暴露 disable/enable 方法。需要软删除时由生产适配器实现。

### DB Partition

`kb_document` 默认不分片。大规模部署时应按 `kb_id` 分区：

```sql
-- MySQL 8.0+
ALTER TABLE kb_document PARTITION BY HASH(kb_id) PARTITIONS 32;

-- 启用分区时，PRIMARY KEY 必须包含分区键：
ALTER TABLE kb_document DROP PRIMARY KEY, ADD PRIMARY KEY (id, kb_id);
```

> 分区 DDL 仅供生产参考，不在默认 schema 中执行。

-- =============================================================================
-- KnowledgeBase RDBMS Schema — SQLite 3
-- =============================================================================
-- kb — aggregate root, holds oss/rdbms/vdb as orchestration targets.
-- oss — original file storage
-- rdbms — document metadata management (this file)
-- vdb — chunk semantic retrieval support
-- =============================================================================
-- SQLite 3 limitations vs MySQL:
--   - No COMMENT on tables/columns    → inline -- comments
--   - No JSON type                    → TEXT
--   - No ON UPDATE CURRENT_TIMESTAMP  → triggers
--   - No PARTITION BY HASH            → omitted (single-file db)
--   - No BIGINT / TINYINT             → INTEGER
--   - No ENGINE / CHARSET             → omitted
-- =============================================================================

-- ---------------------------------------------------------------------------
-- kb_info — Knowledge Base Scope Configurations
-- ---------------------------------------------------------------------------
CREATE TABLE kb_info (
    kb_id       INTEGER PRIMARY KEY,                              -- Knowledge base unique ID
    kb_name     TEXT NOT NULL,                                    -- Knowledge base name
    owner_uid   INTEGER NOT NULL,                                 -- Which user this kb belongs to
    status      INTEGER NOT NULL DEFAULT 1,                       -- 0-disable, 1-enable

    -- Fixed config
    embed_model TEXT NOT NULL,                                    -- Embedding model
    embed_dim   INTEGER NOT NULL,                                 -- Actual dimension
    -- embed version is usually contained in embed_model, defined by model provider

    -- Extern configs, this should be calculated in backend
    ext_config  TEXT,                                             -- Extern configs (JSON stored as TEXT)

    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_kb_info_owner ON kb_info (owner_uid);
CREATE UNIQUE INDEX uk_kb_name_owner ON kb_info (owner_uid, kb_name);

-- Simulate ON UPDATE CURRENT_TIMESTAMP for kb_info.updated_at
CREATE TRIGGER trg_kb_info_update
    AFTER UPDATE ON kb_info
BEGIN
    UPDATE kb_info SET updated_at = datetime('now') WHERE kb_id = NEW.kb_id;
END;


-- ---------------------------------------------------------------------------
-- kb_document — Knowledge Base Documents
-- ---------------------------------------------------------------------------
-- SQLite has no partition support; large-scale deployments should use MySQL.
-- ---------------------------------------------------------------------------
CREATE TABLE kb_document (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,        -- Global document id
    kb_id               INTEGER NOT NULL,                         -- kb_id, fk~kb_info.kb_id (logical)

    title               TEXT NOT NULL,                            -- doc_title
    mime_type           TEXT NOT NULL,                            -- Type (pdf, doc, md ...)
    security_level      INTEGER,                                 -- Security level
    content_hash        TEXT,                                    -- Content hash (SHA-256)

    -- With OSS
    uri                 TEXT NOT NULL,                            -- OSS URI, original content is kept by OSS

    -- With Vector DB
    segment_count       INTEGER DEFAULT 0,                        -- Segment count
    embedding_status    INTEGER DEFAULT 0,                        -- 0-unfinished 1-ok

    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_kb_document_kb ON kb_document (kb_id);
CREATE UNIQUE INDEX uk_kb_doc ON kb_document (kb_id, id);

-- Simulate ON UPDATE CURRENT_TIMESTAMP for kb_document.updated_at
CREATE TRIGGER trg_kb_document_update
    AFTER UPDATE ON kb_document
BEGIN
    UPDATE kb_document SET updated_at = datetime('now') WHERE id = NEW.id;
END;

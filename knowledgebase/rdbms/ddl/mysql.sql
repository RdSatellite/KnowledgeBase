-- =============================================================================
-- KnowledgeBase RDBMS Schema — MySQL 8.0+
-- =============================================================================
-- kb — aggregate root, holds oss/rdbms/vdb as orchestration targets.
-- oss — original file storage
-- rdbms — document metadata management (this file)
-- vdb — chunk semantic retrieval support
-- =============================================================================

-- ---------------------------------------------------------------------------
-- kb_info — Knowledge Base Scope Configurations
-- ---------------------------------------------------------------------------
CREATE TABLE kb_info (
    kb_id       BIGINT PRIMARY KEY,
    kb_name     VARCHAR(256) NOT NULL,
    owner_uid   BIGINT NOT NULL             COMMENT 'Which user this kb belongs to',
    status      TINYINT NOT NULL DEFAULT 1  COMMENT '0-disable, 1-enable',

    -- Fixed config
    embed_model VARCHAR(256) NOT NULL       COMMENT 'Embedding model',
    embed_dim   INT NOT NULL                COMMENT 'Actual dimension',
    -- embed version is usually contained in embed_model, defined by model provider

    -- Extern configs, this should be calculated in backend
    ext_config  JSON                        COMMENT 'Extern configs',

    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_owner (owner_uid),
    UNIQUE KEY uk_kb_name_owner (owner_uid, kb_name)
) COMMENT 'Knowledge base scope configurations';


-- ---------------------------------------------------------------------------
-- kb_document — Knowledge Base Documents
-- ---------------------------------------------------------------------------
CREATE TABLE kb_document (
    id                  BIGINT AUTO_INCREMENT   COMMENT 'Global document id',
    kb_id               BIGINT NOT NULL         COMMENT 'kb_id, fk~kb_info.kb_id (logical)',

    title               VARCHAR(512) NOT NULL   COMMENT 'doc_title',
    mime_type           VARCHAR(256) NOT NULL   COMMENT 'Type (pdf, doc, md ...)',
    security_level      TINYINT                 COMMENT 'Security level',
    content_hash        CHAR(64)                COMMENT 'Content hash (SHA-256)',

    -- With OSS
    uri                 VARCHAR(256) NOT NULL   COMMENT 'OSS URI, original content is kept by OSS',

    -- With Vector DB
    segment_count       INT DEFAULT 0           COMMENT 'Segment count',
    embedding_status    TINYINT DEFAULT 0       COMMENT '0-unfinished 1-ok',

    created_at           DATETIME,
    updated_at           DATETIME,

    PRIMARY KEY (id),
    UNIQUE KEY uk_kb_doc (kb_id, id),
    INDEX idx_kb (kb_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =============================================================================
-- Production partition plan (for reference, not applied by default):
--
-- ALTER TABLE kb_document PARTITION BY HASH(kb_id) PARTITIONS 32;
--
-- When partitioning is enabled, PRIMARY KEY must include the partition key:
--   ALTER TABLE kb_document DROP PRIMARY KEY, ADD PRIMARY KEY (id, kb_id);
-- =============================================================================

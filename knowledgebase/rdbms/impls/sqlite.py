"""
Default Repository implementation backed by SQLite 3.

Zero external dependencies beyond the stdlib.  Suitable for development
and single-machine deployments.  For production, inject a MySQL adapter.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from entity.document import Document
from rdbms.abc import KbConfig, BaseRepository

_DDL_PATH = Path(__file__).resolve().parent.parent / "ddl" / "sqlite.sql"


# --- Helpers --- #

def _parse_dt(raw: str | None) -> datetime | None:
    """Convert a SQLite datetime text to a naive UTC datetime."""
    if raw is None:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _row_to_kbconfig(row: sqlite3.Row) -> KbConfig:
    ext_raw = row["ext_config"]
    return KbConfig(
        kb_id=row["kb_id"],
        kb_name=row["kb_name"],
        owner_uid=row["owner_uid"],
        embed_model=row["embed_model"],
        embed_dim=row["embed_dim"],
        ext_config=json.loads(ext_raw) if ext_raw else None,
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        doc_id=row["id"],
        kb_id=row["kb_id"],
        title=row["title"],
        mime_type=row["mime_type"],
        security_level=row["security_level"] or 0,
        created_at=_parse_dt(row["created_at"]) or datetime.now(),
        updated_at=_parse_dt(row["updated_at"]) or datetime.now(),
        uri=row["uri"],
    )


# --- Repository --- #

class SqliteRepository(BaseRepository):
    """SQLite-backed Repository — default lightweight implementation."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

        table_exists = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("kb_info",),
        ).fetchone()
        if table_exists is None:
            self._conn.executescript(_DDL_PATH.read_text(encoding="utf-8"))
            self._conn.commit()

    # --- Internal helpers --- #

    @staticmethod
    def _require_rows(cur: sqlite3.Cursor, entity: str, **keys: object) -> None:
        """
        Raise LookupError if the last statement affected zero rows.
        
        Effect: UPDATE / DELETE
        """
        if cur.rowcount == 0:
            detail = ", ".join(f"{k}={v!r}" for k, v in keys.items())
            raise LookupError(f"{entity} not found: {detail}")

    # --- Knowledge Base --- #

    def create_kb(
        self,
        owner_uid: int,
        kb_name: str,
        embed_model: str,
        embed_dim: int,
        ext_config: Optional[dict] = None,
    ) -> int:
        ext_json = json.dumps(ext_config) if ext_config is not None else None
        cur = self._conn.execute(
            "INSERT INTO kb_info (kb_name, owner_uid, embed_model, embed_dim, ext_config) "
            "VALUES (?, ?, ?, ?, ?)",
            (kb_name, owner_uid, embed_model, embed_dim, ext_json),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_kb(self, kb_id: int) -> KbConfig:
        row = self._conn.execute(
            "SELECT * FROM kb_info WHERE kb_id = ?", (kb_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"Knowledge base not found: kb_id={kb_id}")
        return _row_to_kbconfig(row)

    def list_kb_by_owner(self, owner_uid: int) -> list[KbConfig]:
        rows = self._conn.execute(
            "SELECT * FROM kb_info WHERE owner_uid = ? ORDER BY kb_id",
            (owner_uid,),
        ).fetchall()
        return [_row_to_kbconfig(r) for r in rows]

    def update_kb(
        self,
        kb_id: int,
        *,
        kb_name: str | None = None,
        ext_config: dict | None = None,
    ) -> None:
        # 1. Prepare updates
        updates: dict[str, object] = {}
        if kb_name is not None:
            updates["kb_name"] = kb_name
        if ext_config is not None:
            updates["ext_config"] = json.dumps(ext_config)

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cur = self._conn.execute(
            f"UPDATE kb_info SET {set_clause} WHERE kb_id = ?",
            (*updates.values(), kb_id),
        )
        self._conn.commit()
        self._require_rows(cur, "Knowledge base", kb_id=kb_id)

    # --- Documents --- #

    def add_document(
        self,
        kb_id: int,
        title: str,
        mime_type: str,
        uri: str,
        content_hash: str,
        *,
        security_level: Optional[int] = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO kb_document "
            "(kb_id, title, mime_type, uri, content_hash, security_level) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kb_id, title, mime_type, uri, content_hash, security_level),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_document(self, kb_id: int, doc_id: int) -> Document:
        row = self._conn.execute(
            "SELECT * FROM kb_document WHERE kb_id = ? AND id = ?",
            (kb_id, doc_id),
        ).fetchone()
        if row is None:
            raise LookupError(
                f"Document not found: kb_id={kb_id}, doc_id={doc_id}"
            )
        return _row_to_document(row)

    def list_documents(self, kb_id: int) -> list[Document]:
        rows = self._conn.execute(
            "SELECT * FROM kb_document WHERE kb_id = ? ORDER BY id",
            (kb_id,),
        ).fetchall()
        return [_row_to_document(r) for r in rows]

    def update_document(
        self,
        kb_id: int,
        doc_id: int,
        *,
        title: Optional[str] = None,
        security_level: Optional[int] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        # 1. Prepare updates
        updates: dict[str, object] = {}
        if title is not None:
            updates["title"] = title
        if security_level is not None:
            updates["security_level"] = security_level
        if content_hash is not None:
            updates["content_hash"] = content_hash

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cur = self._conn.execute(
            f"UPDATE kb_document SET {set_clause} WHERE kb_id = ? AND id = ?",
            (*updates.values(), kb_id, doc_id),
        )
        self._conn.commit()
        
        self._require_rows(cur, "Document", kb_id=kb_id, doc_id=doc_id)

    def remove_document(self, kb_id: int, doc_id: int) -> None:
        cur = self._conn.execute(
            "DELETE FROM kb_document WHERE kb_id = ? AND id = ?",
            (kb_id, doc_id),
        )
        self._conn.commit()
        self._require_rows(cur, "Document", kb_id=kb_id, doc_id=doc_id)

    def mark_embedded(self, kb_id: int, doc_id: int, segment_count: int) -> None:
        cur = self._conn.execute(
            "UPDATE kb_document SET embedding_status = 1, segment_count = ? "
            "WHERE kb_id = ? AND id = ?",
            (segment_count, kb_id, doc_id),
        )
        self._conn.commit()
        self._require_rows(cur, "Document", kb_id=kb_id, doc_id=doc_id)

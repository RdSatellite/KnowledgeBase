from dataclasses import dataclass
from datetime import datetime

@dataclass
class Document:
    """
    Document metadata
    
    Managed by RDBMS, and the truth source is stored in OSS.
    """

    doc_id: int             # Document id
    kb_id: int              # KnowledgeBase id

    title: str              # Title
    mime_type: str          # Type (pdf, doc, md)
    security_level: int     # Security Level
    created_at: datetime
    updated_at: datetime

    uri: str                # OSS uri

    @property
    def filename(self) -> str:
        return f"{self.title}.{self.mime_type}"

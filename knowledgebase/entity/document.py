from dataclasses import dataclass


@dataclass
class Document:
    doc_id: str             # Document id
    kb_id: str              # KnowledgeBase id

    title: str              # Title
    security_level: int     # Security Level


# Ignored attributes
#       mime_type:  oss issue
#       raw_uri:    oss issue
#       created_at: rdbms issue
#       update_at:  rdbms issue
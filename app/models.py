# app/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Float, JSON, ForeignKey

class Base(DeclarativeBase):
    pass

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_tag: Mapped[str] = mapped_column(String, index=True, unique=True)

class DocNode(Base):
    __tablename__ = "doc_nodes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    version_id: Mapped[str] = mapped_column(String, ForeignKey("document_versions.version_tag"), index=True)
    
    heading_number: Mapped[str] = mapped_column(String, nullable=True, index=True)
    heading_title: Mapped[str] = mapped_column(String, nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=True)
    page: Mapped[int] = mapped_column(Integer, nullable=True)
    top: Mapped[float] = mapped_column(Float, nullable=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=True)
    table_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # Added this field to store the sha256 content signatures from finalize_hash()
    content_hash: Mapped[str] = mapped_column(String, nullable=True)
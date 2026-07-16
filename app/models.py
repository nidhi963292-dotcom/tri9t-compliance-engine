# app/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, Float, JSON, ForeignKey

class Base(DeclarativeBase):
    pass

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_tag: Mapped[str] = mapped_column(String, index=True, unique=True)
    
    # Connects document versions cleanly to their child nodes
    nodes = relationship("DocNode", back_populates="version", cascade="all, delete-orphan")

class DocNode(Base):
    __tablename__ = "doc_nodes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_versions.id"), index=True)
    
    heading_number: Mapped[str] = mapped_column(String, nullable=True, index=True)
    heading_title: Mapped[str] = mapped_column(String, nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=True)
    page: Mapped[int] = mapped_column(Integer, nullable=True)
    top: Mapped[float] = mapped_column(Float, nullable=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=True)
    table_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=True)

    version = relationship("DocumentVersion", back_populates="nodes")
    pins = relationship("PinnedSelection", back_populates="node", cascade="all, delete-orphan")

class PinnedSelection(Base):
    __tablename__ = "pinned_selections"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    selection_id: Mapped[str] = mapped_column(String, index=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("doc_nodes.id"), index=True)
    pinned_version_tag: Mapped[str] = mapped_column(String, index=True)
    
    node = relationship("DocNode", back_populates="pins")
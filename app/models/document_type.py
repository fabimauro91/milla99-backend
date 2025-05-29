from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class DocumentTypeBase(SQLModel):
    name: str = Field(unique=True)

class DocumentType(DocumentTypeBase, table=True):
    __tablename__ = "document_type"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    driver_documents: List["DriverDocuments"] = Relationship(back_populates="documenttype")

class DocumentTypeCreate(DocumentTypeBase):
    pass

class DocumentTypeUpdate(SQLModel):
    name: Optional[str] = None 
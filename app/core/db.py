from fastapi import FastAPI
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from .config import settings

# Importar todos los modelos para asegurar que estén registrados
from app.models import Role, UserHasRole, DocumentType, DriverDocuments

engine = create_engine(settings.DATABASE_URL)

def create_all_tables(app: FastAPI):
    # Crear las tablas en orden específico
    DocumentType.metadata.create_all(engine)  # Primero document_type
    Role.metadata.create_all(engine)          # Luego role
    UserHasRole.metadata.create_all(engine)   # Luego user_has_roles
    DriverDocuments.metadata.create_all(engine)  # Finalmente driver_documents
    yield

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)] 
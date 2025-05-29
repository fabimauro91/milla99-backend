from fastapi import FastAPI
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from .config import settings

# ✅ IMPORTAR TODOS LOS MODELOS
from app.models import (
    Role, UserHasRole, DocumentType, DriverInfo, VehicleInfo,
    VehicleType, User, DriverDocuments, ClientRequest, DriverPosition,
    DriverTripOffer, ProjectSettings, Referral, CompanyAccount,
    DriverSavings, Transaction, VerifyMount, TypeService, ConfigServiceValue
)

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_all_tables():
    """Crea todas las tablas en la base de datos"""
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
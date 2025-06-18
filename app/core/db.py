from fastapi import FastAPI
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from .config import settings
import os

# ✅ IMPORTAR TODOS LOS MODELOS
from app.models import (
    Role, UserHasRole, DocumentType, DriverInfo, VehicleInfo,
    VehicleType, User, DriverDocuments, ClientRequest, DriverPosition,
    DriverTripOffer, ProjectSettings, Referral, CompanyAccount,
    DriverSavings, Transaction, VerifyMount, TypeService, ConfigServiceValue
)

# Para la aplicación principal, siempre usar la base de datos de desarrollo
# a menos que se especifique explícitamente que estamos en modo test
if os.getenv("TESTING") == "true":
    # Solo en modo test usar la URL de test
    database_url = "mysql+mysqlconnector://root:root@localhost:3306/milla99_test"
else:
    # Para desarrollo y producción, usar la URL de desarrollo
    database_url = "mysql+mysqlconnector://root:root@localhost:3306/milla99"


engine = create_engine(database_url, echo=False)


def create_all_tables():
    """Crea todas las tablas en la base de datos"""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

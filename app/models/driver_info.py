from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, JSON
from typing import Optional, TYPE_CHECKING, List, Dict
from datetime import date, datetime
from uuid import UUID, uuid4
import pytz

if TYPE_CHECKING:
    from .user import User
    from .vehicle_info import VehicleInfo
    from .driver_documents import DriverDocuments
    from .client_request import ClientRequest


class DriverInfoBase(SQLModel):
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str] = None
    # selfie_url: Optional[str] = None  # Eliminado, ahora está en User


class DriverInfo(DriverInfoBase, table=True):
    __tablename__ = "driver_info"
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver_info")
    vehicle_info: Optional["VehicleInfo"] = Relationship(
        back_populates="driver_info")
    documents: List["DriverDocuments"] = Relationship(
        back_populates="driver_info")

    # Campos para gestión de solicitudes pendientes
    pending_request_id: Optional[UUID] = Field(
        default=None,
        foreign_key="client_request.id",
        description="ID de la solicitud pendiente aceptada por el conductor"
    )
    pending_request_accepted_at: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora cuando el conductor aceptó la solicitud pendiente"
    )

    # ============================================================================
    # CAMPOS PARA VERIFICACIÓN DE DOCUMENTOS
    # ============================================================================
    document_verification_status: Optional[str] = Field(
        default="PENDING",
        description="Estado de verificación de documentos: PENDING, APPROVED, REJECTED, MANUAL_REVIEW"
    )
    document_verification_score: Optional[float] = Field(
        default=0.0,
        description="Puntuación de verificación de documentos (0.0 - 1.0)"
    )
    document_verification_details: Optional[Dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Detalles completos de la verificación de documentos"
    )
    document_verification_date: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora de la última verificación de documentos"
    )
    document_verification_id: Optional[str] = Field(
        default=None,
        description="ID único de la verificación de documentos"
    )
    verification_attempts: int = Field(
        default=0,
        description="Número de intentos de verificación realizados"
    )
    last_verification_attempt: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora del último intento de verificación"
    )

    # Relación con la solicitud pendiente
    pending_request: Optional["ClientRequest"] = Relationship(
        back_populates="driver_pending_request"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(
        pytz.timezone("America/Bogota")), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(pytz.timezone("America/Bogota")),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(
            pytz.timezone("America/Bogota"))}
    )


class DriverInfoCreate(DriverInfoBase):
    pass


class DriverInfoUpdate(SQLModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[str] = None
    # selfie_url: Optional[str] = None  # Eliminado
    pending_request_id: Optional[UUID] = None
    pending_request_accepted_at: Optional[datetime] = None
    # Campos de verificación de documentos
    document_verification_status: Optional[str] = None
    document_verification_score: Optional[float] = None
    document_verification_details: Optional[Dict] = None
    document_verification_date: Optional[datetime] = None
    document_verification_id: Optional[str] = None
    verification_attempts: Optional[int] = None
    last_verification_attempt: Optional[datetime] = None

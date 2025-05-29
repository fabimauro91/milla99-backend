from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar
from sqlalchemy import Column, String, event
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class SavingsType(str, Enum):
    SAVING = "SAVING"
    APPROVED = "APPROVED"


class DriverSavings(SQLModel, table=True):
    _tablename_ = "driver_savings"
    id: Optional[int] = Field(default=None, primary_key=True)
    mount: Optional[int] = Field(default=0)
    user_id: int = Field(foreign_key="user.id")
    status: SavingsType = Field(default="SAVING")
    date_saving: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    # Relación con ClassVar
    user: Optional["User"] = Relationship(back_populates="driver_savings")

# --- Eventos deben ir después de la clase ---


@event.listens_for(DriverSavings, 'before_insert')
def set_created_at(mapper, connection, target):
    now = datetime.utcnow()
    if target.created_at is None:
        target.created_at = now
    target.updated_at = now
    # date_saving siempre es un año después de created_at
    target.date_saving = target.created_at + timedelta(days=365)


@event.listens_for(DriverSavings, 'before_update')
def set_updated_at(mapper, connection, target):
    target.updated_at = datetime.utcnow()
    # Validar que created_at no sea None
    if target.created_at is None:
        raise ValueError(
            "created_at cannot be set to None. It must always have a valid datetime.")
    # Si created_at fue modificado, recalcular date_saving
    if hasattr(target, '_sa_instance_state'):
        history = target._sa_instance_state.get_history('created_at', True)
        if history.has_changes():
            target.date_saving = target.created_at + timedelta(days=365)

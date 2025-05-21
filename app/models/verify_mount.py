from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal
from .driver_payment import DriverPayment
# from .user import User


class PaymentMethod(str, Enum):
    TRANSFER = "transfer"
    CASH = "cash"
    CARD = "card"
    OTHER = "other"


class VerifyMountStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VerifyMount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_payment: int = Field(foreign_key="driverpayment.id")
    id_user: int = Field(foreign_key="user.id")
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    payment_method: PaymentMethod
    payment_reference: str = Field(max_length=100)
    status: VerifyMountStatus = Field(default=VerifyMountStatus.PENDING)
    verified_at: Optional[datetime] = None
    verified_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Corregir las relaciones usando Relationship
    payment: Optional["DriverPayment"] = Relationship(
        back_populates="verify_mounts")
    user: Optional["User"] = Relationship(
        back_populates="verify_mounts",
        sa_relationship_kwargs={"foreign_keys": "[VerifyMount.id_user]"}
    )
    verifier: Optional["User"] = Relationship(
        back_populates="verified_mounts",
        sa_relationship_kwargs={"foreign_keys": "[VerifyMount.verified_by]"}
    )
    transactions: List["DriverTransaction"] = Relationship(
        back_populates="verify_mount")


class VerifyMountCreate(SQLModel):
    id_payment: int
    id_user: int
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    payment_method: PaymentMethod
    payment_reference: str = Field(max_length=100)


class VerifyMountUpdate(SQLModel):
    status: Optional[VerifyMountStatus] = None
    verified_by: Optional[int] = None
    payment_reference: Optional[str] = None

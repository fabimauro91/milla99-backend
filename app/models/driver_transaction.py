from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel
from .driver_payment import PaymentStatus, DriverPayment
from .verify_mount import VerifyMount


class TransactionType(str, Enum):
    BONUS = "BONUS"          # Bono de bienvenida
    DEPOSIT = "DEPOSIT"      # Ingreso de dinero (recarga)
    WITHDRAWAL = "WITHDRAWAL"  # Retiro de dinero
    SERVICE_PAYMENT = "SERVICE_PAYMENT"  # Pago de servicio
    COMMISSION = "COMMISSION"  # Comisión de la plataforma
    REFUND = "REFUND"       # Reembolso
    ADJUSTMENT = "ADJUSTMENT"  # Ajuste manual


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class MovementType(str, Enum):
    INCOME = "INCOME"    # Ingreso
    EXPENSE = "EXPENSE"  # Egreso


class DriverTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_payment: int = Field(foreign_key="driverpayment.id")
    id_verify_mount: Optional[int] = Field(
        default=None, foreign_key="verifymount.id")
    id_user: int = Field(foreign_key="user.id")
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)  # Monto del descuento
    description: str = Field(max_length=255)
    # ID de referencia externo (ej: ID de pago)
    reference_id: Optional[str] = Field(default=None, max_length=100)
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    transaction_date: Optional[datetime] = None  # Fecha real de la transacción
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Corregir las relaciones usando Relationship
    payment: Optional["DriverPayment"] = Relationship(
        back_populates="transactions")
    verify_mount: Optional["VerifyMount"] = Relationship(
        back_populates="transactions")
    user: Optional["User"] = Relationship(back_populates="transactions")

# Modelos Pydantic para operaciones


class DriverTransactionCreate(SQLModel):
    id_payment: int
    id_user: int
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)
    description: str = Field(max_length=255)
    reference_id: Optional[str] = None
    id_verify_mount: Optional[int] = None
    transaction_date: Optional[datetime] = None


class DriverTransactionUpdate(SQLModel):
    status: Optional[TransactionStatus] = None
    reference_id: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    transaction_date: Optional[datetime] = None


class DriverTransactionResponse(BaseModel):
    id: int
    transaction_date: datetime
    transaction_type: TransactionType
    amount: Decimal
    description: str
    status: TransactionStatus
    reference_id: Optional[str]
    movement_type: MovementType  # Campo calculado
    payment_method: Optional[str]  # Para recargas
    payment_reference: Optional[str]  # Para recargas
    verified_at: Optional[datetime]  # Para recargas

    @classmethod
    def from_transaction(cls, transaction: DriverTransaction, verify_mount: Optional[VerifyMount] = None):
        # Determinar el tipo de movimiento basado en el tipo de transacción
        movement_type = (
            MovementType.INCOME
            if transaction.transaction_type in [TransactionType.BONUS, TransactionType.DEPOSIT, TransactionType.REFUND]
            else MovementType.EXPENSE
        )

        return cls(
            id=transaction.id,
            transaction_date=transaction.transaction_date or transaction.created_at,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            description=transaction.description,
            status=transaction.status,
            reference_id=transaction.reference_id,
            movement_type=movement_type,
            payment_method=verify_mount.payment_method if verify_mount else None,
            payment_reference=verify_mount.payment_reference if verify_mount else None,
            verified_at=verify_mount.verified_at if verify_mount else None
        )

    class Config:
        from_attributes = True


class DriverTransactionCreateRequest(BaseModel):
    transaction_type: TransactionType
    amount: Decimal
    description: Optional[str] = None
    # Otros campos opcionales como reference_id, etc.

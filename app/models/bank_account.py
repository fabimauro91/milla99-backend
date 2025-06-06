from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from app.utils.encryption import encryption_service

if TYPE_CHECKING:
    from .user import User
    from .withdrawal import Withdrawal


class AccountType(str, Enum):
    SAVINGS = "savings"
    CHECKING = "checking"


class IdentificationType(str, Enum):
    CC = "CC"  # Cédula de Ciudadanía
    CE = "CE"  # Cédula de Extranjería
    NIT = "NIT"  # Número de Identificación Tributaria


class BankAccountBase(SQLModel):
    """Modelo base con campos no sensibles"""
    bank_id: int = Field(foreign_key="bank.id")
    account_type: AccountType
    account_holder_name: str
    is_active: bool = Field(default=True)
    verification_date: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    type_identification: IdentificationType


class BankAccountCreate(BankAccountBase):
    """Modelo para crear cuenta bancaria con campos sensibles"""
    account_number: str
    identification_number: str

    def encrypt_sensitive_data(self):
        """Encripta los datos sensibles antes de guardar"""
        self.account_number = encryption_service.encrypt(self.account_number)
        self.identification_number = encryption_service.encrypt(
            self.identification_number)
        return self


class BankAccountRead(BankAccountBase):
    """Modelo para leer cuenta bancaria con campos sensibles enmascarados"""
    id: UUID
    user_id: UUID
    account_number: str  # Enmascarado
    identification_number: str  # Enmascarado
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, obj):
        """Convierte el objeto ORM a modelo de lectura con datos enmascarados"""
        data = super().from_orm(obj)
        # Desencriptar y luego enmascarar datos sensibles
        try:
            decrypted_account = obj.get_decrypted_account_number()
            decrypted_id = obj.get_decrypted_identification_number()
            # Enmascarar los últimos 4 dígitos
            data.account_number = f"****{decrypted_account[-4:]}" if decrypted_account else None
            data.identification_number = f"***{decrypted_id[-4:]}" if decrypted_id else None
        except Exception as e:
            # Si hay error al desencriptar, mostrar todo enmascarado
            data.account_number = "**********"
            data.identification_number = "**********"
        return data


class BankAccount(BankAccountBase, table=True):
    """Modelo de base de datos con campos encriptados"""
    __tablename__ = "bank_account"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    account_number: str  # Almacenado encriptado
    identification_number: str  # Almacenado encriptado
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # Relaciones
    user: Optional["User"] = Relationship(back_populates="bank_accounts")
    withdrawals: List["Withdrawal"] = Relationship(
        back_populates="bank_account")

    def get_decrypted_account_number(self) -> str:
        """Obtiene el número de cuenta desencriptado"""
        return encryption_service.decrypt(self.account_number)

    def get_decrypted_identification_number(self) -> str:
        """Obtiene la cédula desencriptada"""
        return encryption_service.decrypt(self.identification_number)

    class Config:
        schema_extra = {
            "example": {
                "bank_id": 4,
                "account_number": "1234567890",
                "account_type": "savings",
                "identification_number": "1234567890",
                "account_holder_name": "John Doe",
                "type_identification": "CC"
            }
        }

from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional

class DriversLicenseBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    expiration_date: datetime
    category: str
    restrictions: str = Field(default="")

class DriversLicense(DriversLicenseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación con el usuario
    user: "User" = Relationship(back_populates="drivers_license")

class DriversLicenseCreate(DriversLicenseBase):
    pass

class DriversLicenseUpdate(SQLModel):
    expiration_date: Optional[datetime] = None
    category: Optional[str] = None
    restrictions: Optional[str] = None

# También necesitarías actualizar tu modelo User para incluir la relación
# En tu archivo de modelo User, agregarías:
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    drivers_license: Optional[DriversLicense] = Relationship(back_populates="user")
    driver_data: Optional["DriverData"] = Relationship(back_populates="drivers_license")
    # ... resto de tus campos existentes
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date
from app.models.user import UserCreate
from app.models.driver_info import DriverInfoCreate
from app.models.vehicle_info import VehicleInfoCreate

if TYPE_CHECKING:
    from .user import User
    from .driver_info import DriverInfo


class DriverBase(SQLModel):
    driver_info_id: Optional[int] = Field(
        default=None, foreign_key="driverinfo.id")


class Driver(DriverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver")
    driver_info: Optional["DriverInfo"] = Relationship(back_populates="driver")


class DriverCreate(DriverBase):
    user_id: int  # necesario para crear



class DriverFullCreate(SQLModel):
    user: UserCreate
    driver_info: DriverInfoCreate
    vehicle_info: VehicleInfoCreate

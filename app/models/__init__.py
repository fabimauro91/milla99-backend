# Módulo models: define las clases y estructuras de datos principales de la aplicación (SQLModel/Pydantic)

from .customer import Customer, CustomerCreate, CustomerUpdate
from .transaction import Transaction, TransactionCreate
from .role import Role
from .user_has_roles import UserHasRole
from .driver import Driver, DriverCreate, DriverUpdate
from .driver_info import DriverInfo, DriverInfoBase
from .vehicle_info import VehicleInfo, VehicleInfoCreate, VehicleInfoUpdate, VehicleType

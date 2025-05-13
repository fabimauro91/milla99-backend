from pydantic import BaseModel
from app.models.user import UserRead
from app.models.driver_info import DriverInfo
from app.models.vehicle_info import VehicleInfo


class DriverFullRead(BaseModel):
    user: UserRead
    driver_info: DriverInfo
    vehicle_info: VehicleInfo

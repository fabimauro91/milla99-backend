from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.user import User, UserCreate, UserRead
from app.models.role import Role
from app.models.driver_info import DriverInfo, DriverInfoCreate
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate
from app.core.db import engine


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver(
        self,
        user_data: UserCreate,
        driver_info_data: DriverInfoCreate,
        vehicle_info_data: VehicleInfoCreate
    ) -> UserRead:
        with Session(engine) as session:
            # 1. Crear el Usuario
            user = User(**user_data.dict())
            session.add(user)
            session.commit()
            session.refresh(user)

            # 2. Asignar el rol DRIVER
            # Asignar el rol DRIVER automáticamente
            driver_role = session.exec(
                select(Role).where(Role.id == "DRIVER")).first()
            if not driver_role:
                raise HTTPException(status_code=500, detail="Rol DRIVER no existe")

            user.roles.append(driver_role)
            session.add(user)
            session.commit()

            # 3. Crear el DriverInfo
            driver_info = DriverInfo(
                **driver_info_data.dict(),
                user_id=user.id
            )
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)

            # 4. Crear el VehicleInfo
            vehicle_info = VehicleInfo(
                **vehicle_info_data.dict(),
                driver_info_id=driver_info.id
            )
            session.add(vehicle_info)
            session.commit()

            # Convertir a dict y luego a UserRead
            user_dict = user.model_dump()
            user_data = UserRead.model_validate(user_dict)
            return user_data

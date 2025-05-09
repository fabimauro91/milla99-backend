from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.user import User, UserCreate, UserRead
from app.models.role import Role
from app.models.driver_info import DriverInfo, DriverInfoCreate
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate
from app.models.driver_full_read import DriverFullRead


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver(
        self,
        user_data: UserCreate,
        driver_info_data: DriverInfoCreate,
        vehicle_info_data: VehicleInfoCreate
    ) -> DriverFullRead:
        # 1. Crear el Usuario
        user = User(**user_data.dict())
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        # 2. Asignar el rol DRIVER
        driver_role = self.session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        if not driver_role:
            raise HTTPException(status_code=500, detail="Rol DRIVER no existe")

        user.roles.append(driver_role)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        _ = user.roles  # Fuerza la carga de la relación

        # 3. Crear el DriverInfo
        driver_info = DriverInfo(
            **driver_info_data.dict(),
            user_id=user.id
        )
        self.session.add(driver_info)
        self.session.commit()
        self.session.refresh(driver_info)

        # 4. Crear el VehicleInfo
        vehicle_info = VehicleInfo(
            **vehicle_info_data.dict(),
            driver_info_id=driver_info.id
        )
        self.session.add(vehicle_info)
        self.session.commit()
        self.session.refresh(vehicle_info)

        # Consultar el usuario actualizado desde la base de datos
        user_db = self.session.exec(
            select(User).where(User.id == user.id)).first()
        _ = user_db.roles  # Fuerza la carga de la relación
        user_dict = user_db.dict()
        user_dict["roles"] = [
            {
                "id": role.id,
                "name": role.name,
                "route": role.route
            }
            for role in user_db.roles
        ]

        return DriverFullRead(
            user=UserRead.model_validate(user_dict),
            driver_info=driver_info,
            vehicle_info=vehicle_info
        )

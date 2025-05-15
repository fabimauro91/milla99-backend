from sqlmodel import Session
from app.models.driver_position import DriverPosition, DriverPositionCreate
from app.models.user import User
from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.role import Role

class DriverPositionService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver_position(self, data: DriverPositionCreate) -> DriverPosition:
        user = self.session.get(User, data.id_driver)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        # Validar que el usuario tenga el rol DRIVER aprobado
        driver_role = self.session.exec(
            select(UserHasRole).where(
                UserHasRole.id_user == data.id_driver,
                UserHasRole.id_rol == "DRIVER",
            )
        ).first()
        if not driver_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El usuario no tiene el rol de conductor aprobado")

        # Verifica si ya existe una posición para este driver
        existing = self.session.get(DriverPosition, data.id_driver)
        point = from_shape(Point(data.lng, data.lat), srid=4326)
        if existing:
            existing.position = point
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        driver_position = DriverPosition(
            id_driver=data.id_driver,
            position=point
        )
        self.session.add(driver_position)
        self.session.commit()
        self.session.refresh(driver_position)
        return driver_position 
from sqlmodel import Session
from app.models.driver_position import DriverPosition, DriverPositionCreate, DriverPositionRead
from app.models.user import User
from fastapi import HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select, text, func
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

    def get_nearby_drivers(self, lat: float, lng: float, max_distance_km: float):
        max_distance_m = max_distance_km * 1000  # Convertir a metros
        driver_point = func.ST_GeomFromText(f'POINT({lng} {lat})', 4326)
        query = (
            self.session.query(
                DriverPosition.id_driver,
                func.ST_X(DriverPosition.position).label("lng"),
                func.ST_Y(DriverPosition.position).label("lat"),
                (func.ST_Distance_Sphere(DriverPosition.position, driver_point) / 1000).label("distance_km")
            )
            .filter(
                func.ST_Distance_Sphere(DriverPosition.position, driver_point) <= max_distance_m
            )
            .order_by("distance_km")
        )
        results = query.all()
        drivers = []
        for row in results:
            drivers.append(DriverPositionRead(
                id_driver=row[0],
                lat=row[2],
                lng=row[1],
                distance_km=round(row[3], 3)
            ))
        return drivers

    def get_driver_position(self, id_driver: int):
        return self.session.get(DriverPosition, id_driver)

    def delete_driver_position(self, id_driver: int):
        obj = self.session.get(DriverPosition, id_driver)
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True 
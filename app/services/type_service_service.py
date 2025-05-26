from sqlmodel import Session, select
from app.models.type_service import TypeService, TypeServiceCreate, AllowedRole
from app.models.vehicle_type import VehicleType
from fastapi import HTTPException
from datetime import datetime


class TypeServiceService:
    def __init__(self, session: Session):
        self.session = session

    def create_type_service(self, type_service: TypeServiceCreate) -> TypeService:
        db_type_service = TypeService(
            name=type_service.name,
            description=type_service.description,
            vehicle_type_id=type_service.vehicle_type_id,
            allowed_role=type_service.allowed_role
        )
        self.session.add(db_type_service)
        self.session.commit()
        self.session.refresh(db_type_service)
        return db_type_service

    def get_type_service(self, type_service_id: int) -> TypeService:
        type_service = self.session.get(TypeService, type_service_id)
        if not type_service:
            raise HTTPException(
                status_code=404, detail="Tipo de servicio no encontrado")
        return type_service

    def get_type_service_by_vehicle_type(self, vehicle_type_id: int) -> list[TypeService]:
        return self.session.query(TypeService).filter(
            TypeService.vehicle_type_id == vehicle_type_id
        ).all()

    def init_default_types(self):
        """Inicializa los tipos de servicio por defecto (car ride y motorcycle ride)"""
        # Verificar si ya existen los tipos por defecto
        car_service = self.session.query(TypeService).filter(
            TypeService.name == "Car_Ride"
        ).first()

        moto_service = self.session.query(TypeService).filter(
            TypeService.name == "Motorcycle_Ride"
        ).first()

        # Obtener los tipos de vehículo
        car_type = self.session.query(VehicleType).filter(
            VehicleType.name == "Car"
        ).first()

        moto_type = self.session.query(VehicleType).filter(
            VehicleType.name == "Motorcycle"
        ).first()

        if not car_type or not moto_type:
            raise HTTPException(
                status_code=500,
                detail="Vehicle types (Car and Motorcycle) must exist before creating service types"
            )

        # Crear car ride si no existe
        if not car_service:
            car_service = TypeService(
                name="Car Ride",
                description="Passenger transportation service by car",
                vehicle_type_id=car_type.id,
                allowed_role=AllowedRole.DRIVER
            )
            self.session.add(car_service)

        # Crear motorcycle ride si no existe
        if not moto_service:
            moto_service = TypeService(
                name="Motorcycle Ride",
                description="Passenger transportation service by motorcycle",
                vehicle_type_id=moto_type.id,
                allowed_role=AllowedRole.DRIVER
            )
            self.session.add(moto_service)

        self.session.commit()

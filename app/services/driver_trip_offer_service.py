from sqlmodel import Session, select, join
from datetime import datetime, date
from typing import List, Dict, Any
from app.models.driver_trip_offer import DriverTripOffer
from app.models.vehicle_info import VehicleInfo, VehicleInfoRead
from app.models.user import User, UserRead, RoleRead
from app.models.driver_info import DriverInfo, DriverInfoRead
from app.models.vehicle_type import VehicleType, VehicleTypeRead
from app.models.client_request import ClientRequest
from app.models.role import Role
from app.models.user_has_roles import UserHasRole
from fastapi import HTTPException
from sqlalchemy import and_
from pydantic import BaseModel

class DriverTripOfferResponse(BaseModel):
    offer_id: int
    fare_offered: float
    time: float
    distance: float
    created_at: datetime
    driver: UserRead

    class Config:
        from_attributes = True

class DriverTripOfferService:
    def __init__(self, db: Session):
        self.db = db

    def create_driver_trip_offer(self, driver_trip_offer_data: dict) -> DriverTripOffer:
        try:
            # Validar que el usuario exista
            id_driver = driver_trip_offer_data.get("id_driver")
            user = self.db.get(User, id_driver)
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")

            # Validar que el usuario sea conductor
            if not user.driver_info:
                raise HTTPException(status_code=403, detail="El usuario no es un conductor registrado")

            # Validar que la solicitud exista
            id_client_request = driver_trip_offer_data.get("id_client_request")
            client_request = self.db.get(ClientRequest, id_client_request)
            if not client_request:
                raise HTTPException(status_code=404, detail="La solicitud del cliente no existe")

            # Crear la oferta
            new_offer = DriverTripOffer(**driver_trip_offer_data)
            self.db.add(new_offer)
            self.db.commit()
            self.db.refresh(new_offer)
            return new_offer
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))




    def get_today_offers_by_client_request(self, client_request_id: int) -> List[Dict[str, Any]]:
        try:
            today = date.today()
            tomorrow = today.replace(day=today.day + 1)

            # Modificamos la consulta para incluir roles
            query = (
                select(DriverTripOffer, User, DriverInfo, VehicleInfo, VehicleType, Role)
                .join(User, DriverTripOffer.id_driver == User.id)
                .outerjoin(DriverInfo, User.id == DriverInfo.user_id)
                .outerjoin(VehicleInfo, DriverInfo.id == VehicleInfo.driver_info_id)
                .outerjoin(VehicleType, VehicleInfo.vehicle_type_id == VehicleType.id)
                .outerjoin(UserHasRole, User.id == UserHasRole.id_user)  # Join con la tabla intermedia
                .outerjoin(Role, UserHasRole.id_rol == Role.id)  # Join con roles
                .where(
                    and_(
                        DriverTripOffer.id_client_request == client_request_id,
                        DriverTripOffer.created_at >= datetime.combine(today, datetime.min.time()),
                        #DriverTripOffer.created_at < datetime.combine(tomorrow, datetime.min.time())
                    )
                )
            )

            results = self.db.execute(query).fetchall()
            offers_with_drivers = []

            # Diccionario para agrupar roles por usuario
            user_roles = {}

            # Primero, agrupamos los roles por usuario
            for result in results:
                offer, user, driver_info, vehicle_info, vehicle_type, role = result
                if role:  # Si hay rol
                    if user.id not in user_roles:
                        user_roles[user.id] = []
                    role_read = RoleRead(
                        id=role.id,
                        name=role.name,
                        route=role.route
                    )
                    if role_read not in user_roles[user.id]:
                        user_roles[user.id].append(role_read)

            # Ahora procesamos los resultados
            processed_users = set()  # Para evitar duplicados
            for result in results:
                offer, user, driver_info, vehicle_info, vehicle_type, role = result

                # Si ya procesamos este usuario en esta oferta, continuamos
                if (offer.id, user.id) in processed_users:
                    continue

                driver_info_read = DriverInfoRead.model_validate(driver_info) if driver_info else None
                vehicle_type_read = VehicleTypeRead.model_validate(vehicle_type) if vehicle_type else None
                vehicle_info_read = None
                if vehicle_info:
                    vehicle_info_read = VehicleInfoRead(
                        id=vehicle_info.id,
                        brand=vehicle_info.brand,
                        model=vehicle_info.model,
                        model_year=vehicle_info.model_year,
                        color=vehicle_info.color,
                        plate=vehicle_info.plate,
                        vehicle_type=vehicle_type_read,
                        created_at=vehicle_info.created_at,
                        updated_at=vehicle_info.updated_at
                    )

                # Obtenemos los roles del usuario
                roles = user_roles.get(user.id, [])

                user_read = UserRead(
                    id=user.id,
                    country_code=user.country_code,
                    phone_number=user.phone_number,
                    is_verified_phone=user.is_verified_phone,
                    is_active=user.is_active,
                    full_name=user.full_name,
                    roles=roles,
                    vehicle_info=vehicle_info_read.model_dump() if vehicle_info_read else None,
                    driver_info=driver_info_read.model_dump() if driver_info_read else None
                )

                offer_dict = {
                    "offer_id": offer.id,
                    "fare_offered": offer.fare_offered,
                    "time": offer.time,
                    "distance": offer.distance,
                    "created_at": offer.created_at.isoformat(),
                    "driver": user_read.model_dump()
                }
                offers_with_drivers.append(offer_dict)
                processed_users.add((offer.id, user.id))
                
            return offers_with_drivers
        except Exception as e:
            print(f"Error en get_today_offers_by_client_request: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def update_fare_offered(self, offer_id: int, driver_id: int, new_fare: float) -> DriverTripOffer:
        try:
            offer = self.db.get(DriverTripOffer, offer_id)
            if not offer:
                raise HTTPException(status_code=404, detail="Oferta no encontrada")
            if offer.id_driver != driver_id:
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permiso para modificar esta oferta"
                )
            offer.fare_offered = new_fare
            self.db.commit()
            self.db.refresh(offer)
            return offer
        except HTTPException as he:
            raise he
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
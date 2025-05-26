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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        # Validar que el usuario tenga el rol DRIVER aprobado
        driver_role = self.session.exec(
            select(UserHasRole).where(
                UserHasRole.id_user == data.id_driver,
                UserHasRole.id_rol == "DRIVER",
            )
        ).first()
        if not driver_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="El usuario no tiene el rol de conductor aprobado")

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
                (func.ST_Distance_Sphere(DriverPosition.position,
                 driver_point) / 1000).label("distance_km")
            )
            .filter(
                func.ST_Distance_Sphere(
                    DriverPosition.position, driver_point) <= max_distance_m
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

    def get_nearby_drivers_by_client_request(self, id_client_request: int):
        from app.models.client_request import ClientRequest
        from app.models.type_service import TypeService
        from app.models.vehicle_info import VehicleInfo
        from app.models.driver_info import DriverInfo
        from app.models.user import User
        from app.services.client_requests_service import wkb_to_coords
        import requests
        from app.core.config import settings

        # 1. Obtener la solicitud de viaje
        client_request = self.session.query(ClientRequest).filter(
            ClientRequest.id == id_client_request).first()
        if not client_request:
            raise HTTPException(
                status_code=404, detail="Client request no encontrada")

        # 2. Obtener el tipo de servicio
        type_service = self.session.query(TypeService).filter(
            TypeService.id == client_request.type_service_id).first()
        if not type_service:
            raise HTTPException(
                status_code=404, detail="Tipo de servicio no encontrado")

        # 3. Obtener el tipo de vehículo requerido
        vehicle_type_id = type_service.vehicle_type_id
        allowed_role = type_service.allowed_role

        # 4. Buscar conductores activos, aprobados, con vehículo compatible y posición actual
        pickup_coords = wkb_to_coords(client_request.pickup_position)
        if not pickup_coords:
            raise HTTPException(
                status_code=400, detail="La solicitud no tiene posición de recogida válida")
        pickup_point = func.ST_GeomFromText(
            f'POINT({pickup_coords["lng"]} {pickup_coords["lat"]})', 4326)

        base_query = (
            self.session.query(User, DriverInfo, VehicleInfo, func.ST_Distance_Sphere(
                DriverInfo.current_position, pickup_point).label("distance"))
            .join(UserHasRole, UserHasRole.id_user == User.id)
            .join(DriverInfo, DriverInfo.user_id == User.id)
            .join(VehicleInfo, VehicleInfo.driver_info_id == DriverInfo.id)
            .filter(
                UserHasRole.id_rol == allowed_role,
                UserHasRole.status == RoleStatus.APPROVED,
                DriverInfo.current_position.isnot(None),
                VehicleInfo.vehicle_type_id == vehicle_type_id
            )
        )
        distance_limit = 5000  # 5km
        base_query = base_query.having(text(f"distance < {distance_limit}"))
        results = []
        query_results = base_query.all()
        for row in query_results:
            user, driver_info, vehicle_info, distance = row
            avg_rating = self.session.query(func.avg(ClientRequest.driver_rating)).filter(
                ClientRequest.id_driver_assigned == user.id, ClientRequest.driver_rating.isnot(None)).scalar() or 0.0
            driver_position = wkb_to_coords(driver_info.current_position)
            result = {
                "user_id": user.id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "driver_info": {
                    "id": driver_info.id,
                    "first_name": driver_info.first_name,
                    "last_name": driver_info.last_name,
                    "email": driver_info.email,
                    "selfie_url": getattr(driver_info, "selfie_url", None)
                },
                "vehicle_info": {
                    "id": vehicle_info.id,
                    "brand": vehicle_info.brand,
                    "model": vehicle_info.model,
                    "model_year": vehicle_info.model_year,
                    "color": vehicle_info.color,
                    "plate": vehicle_info.plate,
                    "vehicle_type_id": vehicle_info.vehicle_type_id
                },
                "current_position": driver_position,
                "distance_meters": float(distance) if distance is not None else None,
                "rating": float(avg_rating)
            }
            results.append(result)

        # Google Distance Matrix (opcional)
        if results:
            driver_positions = [
                f"{r['current_position']['lat']},{r['current_position']['lng']}" for r in results if r['current_position']]
            origins = '|'.join(driver_positions)
            destination = f"{pickup_coords['lat']},{pickup_coords['lng']}"
            url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
            params = {
                'origins': origins,
                'destinations': destination,
                'units': 'metric',
                'key': settings.GOOGLE_API_KEY,
                'mode': 'driving'
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                google_data = response.json()
                if google_data.get('status') == 'OK':
                    elements = google_data['rows']
                    for i, element in enumerate(elements):
                        if i < len(results):
                            results[i]['google_distance_matrix'] = element['elements'][0]

        return {
            "client_request_id": client_request.id,
            "pickup_position": pickup_coords,
            "type_service": {
                "id": type_service.id,
                "name": type_service.name,
                "vehicle_type_id": type_service.vehicle_type_id,
                "allowed_role": type_service.allowed_role
            },
            "nearby_drivers": results
        }

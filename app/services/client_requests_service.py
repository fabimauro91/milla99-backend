from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from app.models.client_request import ClientRequest, ClientRequestCreate, StatusEnum
from app.models.user import User
from sqlalchemy import func, text
from geoalchemy2.functions import ST_Distance_Sphere
from datetime import datetime, timedelta, timezone
import requests
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.driver_info import DriverInfo
from app.models.vehicle_info import VehicleInfo
from sqlalchemy.orm import selectinload
import traceback
from app.models.type_service import TypeService


def create_client_request(db: Session, data: ClientRequestCreate, id_client: int):
    pickup_point = from_shape(
        Point(data.pickup_lng, data.pickup_lat), srid=4326)
    destination_point = from_shape(
        Point(data.destination_lng, data.destination_lat), srid=4326)
    db_obj = ClientRequest(
        id_client=id_client,
        fare_offered=data.fare_offered,
        fare_assigned=data.fare_assigned,
        pickup_description=data.pickup_description,
        destination_description=data.destination_description,
        client_rating=data.client_rating,
        driver_rating=data.driver_rating,
        pickup_position=pickup_point,
        destination_position=destination_point,
        type_service_id=data.type_service_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_time_and_distance_service(origin_lat, origin_lng, destination_lat, destination_lng):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{destination_lat},{destination_lng}",
        "units": "metric",
        "key": settings.GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Error en el API de Google Distance Matrix: {response.status_code}")
    data = response.json()
    if data.get("status") != "OK":
        raise HTTPException(status_code=status.HTTP_200_OK,
                            detail=f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}")
    return data


def get_nearby_client_requests_service(driver_lat, driver_lng, session: Session, wkb_to_coords, type_service_ids=None):
    driver_point = func.ST_GeomFromText(
        f'POINT({driver_lng} {driver_lat})', 4326)
    time_limit = datetime.now(timezone.utc) - \
        timedelta(minutes=10080)  # 7 días
    distance_limit = 5000
    base_query = (
        session.query(
            ClientRequest,
            User.full_name,
            User.country_code,
            User.phone_number,
            TypeService.name.label("type_service_name"),
            ST_Distance_Sphere(ClientRequest.pickup_position,
                               driver_point).label("distance"),
            func.timestampdiff(
                text('MINUTE'),
                ClientRequest.updated_at,
                func.utc_timestamp()
            ).label("time_difference")
        )
        .join(User, User.id == ClientRequest.id_client)
        .join(TypeService, TypeService.id == ClientRequest.type_service_id)
        .filter(
            ClientRequest.status == "CREATED",
            ClientRequest.updated_at > time_limit
        )
    )
    if type_service_ids:
        base_query = base_query.filter(
            ClientRequest.type_service_id.in_(type_service_ids))
    base_query = base_query.having(text(f"distance < {distance_limit}"))
    results = []
    query_results = base_query.all()
    for row in query_results:
        cr, full_name, country_code, phone_number, type_service_name, distance, time_difference = row
        result = {
            "id": cr.id,
            "id_client": cr.id_client,
            "fare_offered": cr.fare_offered,
            "pickup_description": cr.pickup_description,
            "destination_description": cr.destination_description,
            "status": cr.status,
            "updated_at": cr.updated_at.isoformat(),
            "pickup_position": wkb_to_coords(cr.pickup_position),
            "destination_position": wkb_to_coords(cr.destination_position),
            "distance": float(distance) if distance is not None else None,
            "time_difference": int(time_difference) if time_difference is not None else None,
            "type_service_id": cr.type_service_id,
            "type_service_name": type_service_name,
            "client": {
                "full_name": full_name,
                "country_code": country_code,
                "phone_number": phone_number
            }
        }
        results.append(result)
    return results


def assign_driver_service(session: Session, id: int, id_driver_assigned: int, fare_assigned: float = None):
    # Validación: El conductor debe tener el rol DRIVER y status APPROVED
    try:
        user_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == id_driver_assigned,
            UserHasRole.id_rol == "DRIVER"
        ).first()

        print("DEBUG user_role:", user_role)
        if user_role:
            print("DEBUG user_role.status:", user_role.status)

        if not user_role or user_role.status != RoleStatus.APPROVED:
            print("DEBUG: No tiene rol DRIVER aprobado")
            raise HTTPException(
                status_code=400,
                detail="El usuario no tiene el rol de conductor aprobado. No se puede asignar como conductor."
            )
        client_request = session.query(ClientRequest).filter(
            ClientRequest.id == id).first()
        if not client_request:
            raise HTTPException(
                status_code=404, detail="Solicitud no encontrada")
        client_request.id_driver_assigned = id_driver_assigned
        client_request.status = "ACCEPTED"
        client_request.updated_at = datetime.utcnow()
        if fare_assigned is not None:
            client_request.fare_assigned = fare_assigned
        session.commit()
        return {"success": True, "message": "Conductor asignado correctamente"}
    except Exception as e:
        print("TRACEBACK:")
        print(traceback.format_exc())
        raise


def update_status_service(session: Session, id_client_request: int, status: str):
    client_request = session.query(ClientRequest).filter(
        ClientRequest.id == id_client_request).first()
    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    client_request.status = status
    client_request.updated_at = datetime.utcnow()
    session.commit()
    return {"success": True, "message": "Status actualizado correctamente"}


def get_client_request_detail_service(session: Session, client_request_id: int):
    """
    Devuelve el detalle de una Client Request, incluyendo info de usuario, driver y vehículo si aplica.
    """
    from app.models.user import User
    from app.models.client_request import ClientRequest

    # Buscar la solicitud
    cr = session.query(ClientRequest).filter(
        ClientRequest.id == client_request_id).first()
    if not cr:
        raise HTTPException(
            status_code=404, detail="Client Request no encontrada")

    # Buscar el usuario que la creó
    user = session.query(User).filter(User.id == cr.id_client).first()
    client_data = {
        "id": user.id,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "country_code": user.country_code
    } if user else None

    # Buscar info del conductor asignado (si existe)
    driver_info = None
    vehicle_info = None
    if cr.id_driver_assigned:
        driver = session.query(User).filter(
            User.id == cr.id_driver_assigned).first()
        if driver and driver.driver_info:
            di = driver.driver_info
            driver_info = {
                "id": di.id,
                "first_name": di.first_name,
                "last_name": di.last_name,
                "email": di.email,
                "selfie_url": di.selfie_url
            }
            if di.vehicle_info:
                vi = di.vehicle_info
                vehicle_info = {
                    "brand": vi.brand,
                    "model": vi.model,
                    "model_year": vi.model_year,
                    "color": vi.color,
                    "plate": vi.plate,
                    "vehicle_type_id": vi.vehicle_type_id
                }

    return {
        "id": cr.id,
        "status": str(cr.status),
        "fare_offered": cr.fare_offered,
        "pickup_description": cr.pickup_description,
        "destination_description": cr.destination_description,
        "created_at": cr.created_at.isoformat(),
        "updated_at": cr.updated_at.isoformat(),
        "client": client_data,
        "id_driver_assigned": cr.id_driver_assigned,
        "driver_info": driver_info,
        "vehicle_info": vehicle_info
    }


def get_client_requests_by_status_service(session: Session, status: str):
    """
    Devuelve una lista de client_request filtrados por el estatus enviado en el parámetro.
    """
    from app.models.client_request import ClientRequest
    results = session.query(ClientRequest).filter(
        ClientRequest.status == status).all()
    # Puedes personalizar la respuesta según lo que quieras mostrar
    return [
        {
            "id": cr.id,
            "id_client": cr.id_client,
            "id_driver_assigned": cr.id_driver_assigned,
            "fare_offered": cr.fare_offered,
            "fare_assigned": cr.fare_assigned,
            "pickup_description": cr.pickup_description,
            "destination_description": cr.destination_description,
            "client_rating": cr.client_rating,
            "driver_rating": cr.driver_rating,
            "status": str(cr.status),
            "created_at": cr.created_at.isoformat(),
            "updated_at": cr.updated_at.isoformat()
        }
        for cr in results
    ]


def update_client_rating_service(session: Session, id_client_request: int, client_rating: float, user_id: int):
    client_request = session.query(ClientRequest).filter(
        ClientRequest.id == id_client_request).first()
    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if client_request.id_driver_assigned != user_id:
        raise HTTPException(
            status_code=403, detail="Solo el conductor asignado puede calificar al cliente")
    client_request.client_rating = client_rating
    client_request.updated_at = datetime.utcnow()
    session.commit()
    return {"success": True, "message": "Calificación del cliente actualizada correctamente"}


def update_driver_rating_service(session: Session, id_client_request: int, driver_rating: float, user_id: int):
    client_request = session.query(ClientRequest).filter(
        ClientRequest.id == id_client_request).first()
    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if client_request.id_client != user_id:
        raise HTTPException(
            status_code=403, detail="Solo el cliente puede calificar al conductor")
    client_request.driver_rating = driver_rating
    client_request.updated_at = datetime.utcnow()
    session.commit()
    return {"success": True, "message": "Calificación del conductor actualizada correctamente"}


def assign_driver(self, client_request_id: int, driver_id: int):
    """Asigna un conductor a una solicitud de cliente"""
    client_request = self.session.query(ClientRequest).filter(
        ClientRequest.id == client_request_id
    ).first()

    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if client_request.id_driver_assigned:
        raise HTTPException(
            status_code=400, detail="La solicitud ya tiene un conductor asignado")

    # Verificar que el usuario es un conductor
    driver = self.session.query(User).filter(
        User.id == driver_id,
        User.role == "DRIVER"
    ).first()

    if not driver:
        raise HTTPException(
            status_code=400, detail="El usuario no es un conductor")

    # Verificar que el conductor tiene un vehículo del tipo correcto
    driver_vehicle = self.session.query(VehicleInfo).filter(
        VehicleInfo.user_id == driver_id,
        VehicleInfo.vehicle_type_id == client_request.type_service.vehicle_type_id
    ).first()

    if not driver_vehicle:
        raise HTTPException(
            status_code=400,
            detail="El conductor no tiene un vehículo del tipo requerido para este servicio"
        )

    client_request.id_driver_assigned = driver_id
    client_request.status = StatusEnum.ACCEPTED
    self.session.add(client_request)
    self.session.commit()
    self.session.refresh(client_request)
    return client_request


def get_nearby_requests(self, driver_id: int, lat: float, lng: float, max_distance: float = 5.0):
    """Obtiene las solicitudes cercanas al conductor, filtrando por tipo de servicio"""
    # Obtener el vehículo del conductor
    driver_vehicle = self.session.query(VehicleInfo).filter(
        VehicleInfo.user_id == driver_id
    ).first()

    if not driver_vehicle:
        raise HTTPException(
            status_code=400,
            detail="El conductor no tiene un vehículo registrado"
        )

    # Obtener el tipo de servicio que puede manejar el conductor
    type_services = self.session.query(TypeService).filter(
        TypeService.vehicle_type_id == driver_vehicle.vehicle_type_id
    ).all()

    if not type_services:
        raise HTTPException(
            status_code=400,
            detail="No hay servicios disponibles para el tipo de vehículo del conductor"
        )

    type_service_ids = [ts.id for ts in type_services]

    # Obtener las solicitudes cercanas del tipo de servicio correspondiente
    nearby_requests = self.session.query(ClientRequest).filter(
        ClientRequest.status == StatusEnum.CREATED,
        ClientRequest.type_service_id.in_(type_service_ids),
        func.ST_Distance(
            func.ST_SetSRID(func.ST_MakePoint(
                ClientRequest.pickup_lng, ClientRequest.pickup_lat), 4326),
            func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        ) <= max_distance
    ).all()

    return nearby_requests


def get_nearby_drivers_service(
    client_lat: float,
    client_lng: float,
    type_service_id: int,
    session: Session,
    wkb_to_coords
) -> list:
    """
    Obtiene los conductores cercanos a un cliente en un radio de 5km.

    Args:
        client_lat: Latitud del cliente
        client_lng: Longitud del cliente
        type_service_id: ID del tipo de servicio solicitado
        session: Sesión de base de datos
        wkb_to_coords: Función para convertir WKB a coordenadas

    Returns:
        Lista de conductores cercanos con su información
    """
    try:
        # 1. Obtener el tipo de servicio para validar el tipo de vehículo
        type_service = session.query(TypeService).filter(
            TypeService.id == type_service_id
        ).first()

        if not type_service:
            raise HTTPException(
                status_code=404,
                detail="Tipo de servicio no encontrado"
            )

        # 2. Crear punto del cliente
        client_point = func.ST_GeomFromText(
            f'POINT({client_lng} {client_lat})', 4326)

        # 3. Consulta base para obtener conductores cercanos
        base_query = (
            session.query(
                User,
                DriverInfo,
                VehicleInfo,
                ST_Distance_Sphere(DriverInfo.current_position,
                                   client_point).label("distance")
            )
            .join(UserHasRole, UserHasRole.id_user == User.id)
            .join(DriverInfo, DriverInfo.user_id == User.id)
            .join(VehicleInfo, VehicleInfo.driver_info_id == DriverInfo.id)
            .filter(
                UserHasRole.id_rol == "DRIVER",
                UserHasRole.status == RoleStatus.APPROVED,
                DriverInfo.is_active == True,
                DriverInfo.current_position.isnot(None),
                VehicleInfo.vehicle_type_id == type_service.vehicle_type_id
            )
        )

        # 4. Filtrar por distancia (5km)
        distance_limit = 5000  # 5km en metros
        base_query = base_query.having(text(f"distance < {distance_limit}"))

        # 5. Ejecutar consulta
        results = []
        query_results = base_query.all()

        for row in query_results:
            user, driver_info, vehicle_info, distance = row

            # Calcular calificación promedio del conductor
            avg_rating = session.query(
                func.avg(ClientRequest.driver_rating)
            ).filter(
                ClientRequest.id_driver_assigned == user.id,
                ClientRequest.driver_rating.isnot(None)
            ).scalar() or 0.0

            result = {
                "id": user.id,
                "driver_info": {
                    "id": driver_info.id,
                    "first_name": driver_info.first_name,
                    "last_name": driver_info.last_name,
                    "email": driver_info.email,
                    "selfie_url": driver_info.selfie_url,
                    "current_position": wkb_to_coords(driver_info.current_position)
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
                "distance": float(distance) if distance is not None else None,
                "rating": float(avg_rating),
                "phone_number": user.phone_number,
                "country_code": user.country_code
            }
            results.append(result)

        # 6. Obtener tiempos estimados de Google Distance Matrix
        if results:
            driver_positions = [
                f"{r['driver_info']['current_position']['lat']},{r['driver_info']['current_position']['lng']}"
                for r in results
            ]
            origins = '|'.join(driver_positions)
            destination = f"{client_lat},{client_lng}"

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

        return results

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[ERROR] Exception en get_nearby_drivers_service: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar conductores cercanos: {str(e)}"
        )

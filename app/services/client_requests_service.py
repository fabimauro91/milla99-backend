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
from app.utils.geo_utils import wkb_to_coords


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


def get_nearby_client_requests_service(driver_lat, driver_lng, session: Session, wkb_to_coords):
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
            ST_Distance_Sphere(ClientRequest.pickup_position,
                               driver_point).label("distance"),
            func.timestampdiff(
                text('MINUTE'),
                ClientRequest.updated_at,
                func.utc_timestamp()
            ).label("time_difference")
        )
        .join(User, User.id == ClientRequest.id_client)
        .filter(
            ClientRequest.status == "CREATED",
            ClientRequest.updated_at > time_limit
        )
        .having(text(f"distance < {distance_limit}"))
    )
    results = []
    query_results = base_query.all()
    for row in query_results:
        cr, full_name, country_code, phone_number, distance, time_difference = row
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
        "pickup_position": wkb_to_coords(cr.pickup_position),
        "destination_position": wkb_to_coords(cr.destination_position),
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
            "pickup_position": wkb_to_coords(cr.pickup_position),
            "destination_position": wkb_to_coords(cr.destination_position),
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

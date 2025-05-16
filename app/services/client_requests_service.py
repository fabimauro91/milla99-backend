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
from app.models.user_has_roles import UserHasRole
from app.models.driver_info import DriverInfo
from app.models.vehicle_info import VehicleInfo
from sqlalchemy.orm import selectinload
import traceback


def create_client_request(db: Session, data: ClientRequestCreate):
    pickup_point = from_shape(
        Point(data.pickup_lng, data.pickup_lat), srid=4326)
    destination_point = from_shape(
        Point(data.destination_lng, data.destination_lat), srid=4326)
    db_obj = ClientRequest(
        id_client=data.id_client,
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


def get_time_and_distance_prueba_service():
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "Boston, Massachusetts, EE. UU.",
        "destinations": "Nueva York, EE. UU.",
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
    client_request = session.query(ClientRequest).filter(
        ClientRequest.id == id).first()
    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    client_request.id_driver_assigned = id_driver_assigned
    client_request.status = "ACCEPTED"
    client_request.updated_at = datetime.utcnow()
    if fare_assigned is not None:
        client_request.fare_assigned = fare_assigned
    session.commit()
    return {"success": True, "message": "Conductor asignado correctamente"}


def update_status_service(session: Session, id_client_request: int, status: str):
    client_request = session.query(ClientRequest).filter(
        ClientRequest.id == id_client_request).first()
    if not client_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    client_request.status = status
    client_request.updated_at = datetime.utcnow()
    session.commit()
    return {"success": True, "message": "Status actualizado correctamente"}


def get_driver_vehicle_info_service(session: Session, driver_id: int, user_id: int):
    """
    Obtiene la información del vehículo de un conductor.
    Verifica que el conductor esté asignado a alguna solicitud activa.
    """
    try:
        # Verificar si el conductor está asignado a alguna solicitud activa
        active_request = session.query(ClientRequest).filter(
            ClientRequest.id_driver_assigned == driver_id,
            ClientRequest.status.in_([
                StatusEnum.ACCEPTED,
                StatusEnum.ON_THE_WAY,
                StatusEnum.ARRIVED,
                StatusEnum.TRAVELLING
            ])
        ).first()

        if not active_request:
            print("DEBUG: No active request found for driver_id", driver_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró ninguna solicitud activa asignada a este conductor"
            )

        # Obtener la información del conductor y su vehículo
        driver = session.query(User).options(
            selectinload(User.driver_info).selectinload(
                DriverInfo.vehicle_info)
        ).filter(User.id == driver_id).first()

        print("DEBUG driver:", driver)
        print("DEBUG driver_info:", getattr(driver, 'driver_info', None))
        if getattr(driver, 'driver_info', None):
            print("DEBUG vehicle_info:", getattr(
                driver.driver_info, 'vehicle_info', None))

        if not driver:
            print("DEBUG: No driver found with id", driver_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conductor no encontrado"
            )

        if not driver.driver_info or not driver.driver_info.vehicle_info:
            print("DEBUG: Falta driver_info o vehicle_info para el driver", driver_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El conductor no tiene información de vehículo registrada"
            )

        return {
            "request_id": active_request.id,
            "request_status": str(active_request.status),
            "driver": {
                "id": driver.id,
                "full_name": driver.full_name,
                "phone_number": driver.phone_number,
                "country_code": driver.country_code
            },
            "vehicle_info": {
                "brand": driver.driver_info.vehicle_info.brand,
                "model": driver.driver_info.vehicle_info.model,
                "model_year": driver.driver_info.vehicle_info.model_year,
                "color": driver.driver_info.vehicle_info.color,
                "plate": driver.driver_info.vehicle_info.plate,
                "vehicle_type_id": driver.driver_info.vehicle_info.vehicle_type_id
            }
        }
    except Exception as e:
        print("TRACEBACK:")
        print(traceback.format_exc())
        raise

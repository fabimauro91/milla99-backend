from fastapi import APIRouter, HTTPException, status, Depends, Request, Query, Body
from fastapi.responses import JSONResponse
from app.core.db import get_session
from app.models.client_request import ClientRequest, ClientRequestCreate
from app.services.client_requests_service import (
    create_client_request,
    get_time_and_distance_service,
    get_time_and_distance_prueba_service,
    get_nearby_client_requests_service,
    assign_driver_service,
    update_status_service,
    get_client_request_detail_service
)
from sqlalchemy.orm import Session
import traceback
from pydantic import BaseModel
from app.models.user_has_roles import UserHasRole, RoleStatus

router = APIRouter(prefix="/client-request", tags=["client-request"])


class Position(BaseModel):
    lat: float
    lng: float


class ClientRequestResponse(BaseModel):
    id: int
    id_client: int
    fare_offered: float | None = None
    fare_assigned: float | None = None
    pickup_description: str | None = None
    destination_description: str | None = None
    client_rating: float | None = None
    driver_rating: float | None = None
    status: str
    pickup_position: Position | None = None
    destination_position: Position | None = None
    created_at: str
    updated_at: str

# Utilidad para convertir WKBElement a dict lat/lng


def wkb_to_coords(wkb):
    """
    Convierte un campo WKBElement a un diccionario con latitud y longitud.
    Args:
        wkb: WKBElement de la base de datos
    Returns:
        dict con 'lat' y 'lng' o None si wkb es None
    """
    from geoalchemy2.shape import to_shape
    if wkb is None:
        return None
    point = to_shape(wkb)
    return {"lat": point.y, "lng": point.x}


@router.get("/distance")
def get_time_and_distance(
    origin_lat: float = Query(..., example=4.718136,
                              description="Latitud de origen"),
    origin_lng: float = Query(..., example=-74.07317,
                              description="Longitud de origen"),
    destination_lat: float = Query(..., example=4.702468,
                                   description="Latitud de destino"),
    destination_lng: float = Query(..., example=-
                                   74.109776, description="Longitud de destino")
):
    """
    Consulta la distancia y el tiempo estimado entre dos puntos usando Google Distance Matrix API.
    Args:
        origin_lat: Latitud de origen
        origin_lng: Longitud de origen
        destination_lat: Latitud de destino
        destination_lng: Longitud de destino
    Returns:
        Respuesta JSON de Google Distance Matrix
    """
    try:
        return get_time_and_distance_service(origin_lat, origin_lng, destination_lat, destination_lng)
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(e)})


@router.get("/distance/prueba")
def get_time_and_distance_prueba():
    """
    Endpoint de prueba para consultar distancia y tiempo entre Boston y Nueva York usando Google Distance Matrix API.
    Returns:
        Respuesta JSON de Google Distance Matrix
    """
    try:
        return get_time_and_distance_prueba_service()
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(e)})


@router.get("/nearby")
def get_nearby_client_requests(
    driver_lat: float = Query(..., example=4.708822,
                              description="Latitud del conductor"),
    driver_lng: float = Query(..., example=-74.076542,
                              description="Longitud del conductor"),
    session=Depends(get_session)
):
    """
    Obtiene las solicitudes de viaje cercanas a un conductor en un radio de 5km y los enriquece con la distancia y tiempo estimado usando Google Distance Matrix API.
    Args:
        driver_lat: Latitud del conductor
        driver_lng: Longitud del conductor
    Returns:
        Lista de solicitudes cercanas con información de distancia, tiempo y datos del cliente
    """
    try:
        results = get_nearby_client_requests_service(
            driver_lat, driver_lng, session, wkb_to_coords)
        if not results:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"No hay solicitudes de viaje activas en un radio de 5000 metros",
                    "data": []
                }
            )
        # Google Distance Matrix
        pickup_positions = [
            f"{r['pickup_position']['lat']},{r['pickup_position']['lng']}" for r in results]
        origins = f"{driver_lat},{driver_lng}"
        destinations = '|'.join(pickup_positions)
        import requests
        from app.core.config import settings
        url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
        params = {
            'destinations': destinations,
            'origins': origins,
            'units': 'metric',
            'key': settings.GOOGLE_API_KEY,
            'mode': 'driving'
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "message": f"Error en el API de Google Distance Matrix: {response.status_code}"}
            )
        google_data = response.json()
        if google_data.get('status') != 'OK':
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Error en la respuesta del API de Google Distance Matrix: {google_data.get('status')}"}
            )
        elements = google_data['rows'][0]['elements']
        for index, element in enumerate(elements):
            results[index]['google_distance_matrix'] = element
        return JSONResponse(content=results, status_code=200)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al buscar solicitudes cercanas: {str(e)}")


@router.post("/", response_model=ClientRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    request: Request,
    request_data: ClientRequestCreate = Body(
        ...,
        example={
            "id_client": 1,
            "fare_offered": 20.0,
            "fare_assigned": 25.0,
            "pickup_description": "Suba Bogotá",
            "destination_description": "Santa Rosita Engativa, Bogota",
            "client_rating": 4.5,
            "driver_rating": 4.8,
            "pickup_lat": 4.718136,
            "pickup_lng": -74.07317,
            "destination_lat": 4.702468,
            "destination_lng": -74.109776
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Crea una nueva solicitud de viaje para un cliente.
    Args:
        request_data: Datos de la solicitud (pickup, destino, tarifa, etc.)
        request: Objeto de la petición HTTP (usado para obtener el usuario autenticado)
        session: Sesión de base de datos
    Returns:
        Objeto de la solicitud creada
    """
    try:
        user_id = request.state.user_id

        # Validación: El usuario debe tener el rol CLIENT y status APPROVED
        user_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id,
            UserHasRole.id_rol == "CLIENT"
        ).first()
        if not user_role or user_role.status != RoleStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail="El usuario no tiene el rol de cliente aprobado. No puede crear solicitudes."
            )

        if hasattr(request_data, 'id_client'):
            request_data.id_client = user_id
        db_obj = create_client_request(session, request_data)
        response = {
            "id": db_obj.id,
            "id_client": db_obj.id_client,
            "fare_offered": db_obj.fare_offered,
            "fare_assigned": db_obj.fare_assigned,
            "pickup_description": db_obj.pickup_description,
            "destination_description": db_obj.destination_description,
            "client_rating": db_obj.client_rating,
            "driver_rating": db_obj.driver_rating,
            "status": str(db_obj.status),
            "pickup_position": wkb_to_coords(db_obj.pickup_position),
            "destination_position": wkb_to_coords(db_obj.destination_position),
            "created_at": db_obj.created_at.isoformat(),
            "updated_at": db_obj.updated_at.isoformat(),
        }
        return response
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error al crear la solicitud de viaje: {str(e)}"
        )


@router.patch("/updateDriverAssigned")
def assign_driver(
    id: int = Body(...,
                   description="ID de la solicitud de viaje (id_client_request)"),
    id_driver_assigned: int = Body(...,
                                   description="ID del conductor asignado"),
    fare_assigned: float = Body(
        None, description="Tarifa asignada (opcional)"),
    session: Session = Depends(get_session)
):
    """
    Asigna un conductor a una solicitud de viaje existente, cambia el estado a cualquiera de los estados
    "CREATED", "ACCEPTED", "ON_THE_WAY", "ARRIVED", "TRAVELLING", "FINISHED", "CANCELLED"
    y actualiza la tarifa si se proporciona.

    Args:
        id: ID de la solicitud de viaje (id_client_request)
        id_driver_assigned: ID del conductor asignado
        fare_assigned: Tarifa asignada (opcional)
        session: Sesión de base de datos
    Returns:
        Mensaje de éxito o error
    """
    try:
        return assign_driver_service(session, id, id_driver_assigned, fare_assigned)
    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al asignar conductor: {str(e)}")


@router.patch("/updateStatus")
def update_status(
    id_client_request: int = Body(...,
                                  description="ID de la solicitud de viaje"),
    status: str = Body(..., description="Nuevo estado a asignar"),
    session: Session = Depends(get_session)
):
    """
    Actualiza el estado de una solicitud de viaje existente.
    Args:
        id_client_request: ID de la solicitud de viaje
        status: Nuevo estado a asignar
        session: Sesión de base de datos
    Returns:
        Mensaje de éxito o error
    """
    try:
        return update_status_service(session, id_client_request, status)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar el status: {str(e)}")


@router.get("/{client_request_id}")
def get_client_request_detail(
    client_request_id: int,
    session: Session = Depends(get_session)
):
    """
    Consulta el estado y la información detallada de una Client Request específica.
    """
    return get_client_request_detail_service(session, client_request_id)

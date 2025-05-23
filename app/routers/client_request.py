from fastapi import APIRouter, HTTPException, status, Depends, Request, Query, Body, Path
from fastapi.responses import JSONResponse
from app.core.db import get_session
from app.models.client_request import ClientRequest, ClientRequestCreate, StatusEnum
from app.services.client_requests_service import (
    create_client_request,
    get_time_and_distance_service,
    get_nearby_client_requests_service,
    assign_driver_service,
    update_status_service,
    get_client_request_detail_service,
    get_client_requests_by_status_service,
    update_client_rating_service,
    update_driver_rating_service
)
from sqlalchemy.orm import Session
import traceback
from pydantic import BaseModel, Field
from app.models.user_has_roles import UserHasRole, RoleStatus
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from app.utils.geo_utils import wkb_to_coords

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/client-request",
    tags=["client-request"],
    dependencies=[Security(bearer_scheme)]
)


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


class AssignDriverRequest(BaseModel):
    id: int = Field(..., description="ID de la solicitud de viaje")
    id_driver_assigned: int = Field(..., description="ID del conductor asignado")
    fare_assigned: float | None = Field(None, description="Tarifa asignada (opcional)")


# Utilidad para convertir WKBElement a dict lat/lng


# def wkb_to_coords(wkb):
#     """
#     Convierte un campo WKBElement a un diccionario con latitud y longitud.
#     Args:
#         wkb: WKBElement de la base de datos
#     Returns:
#         dict con 'lat' y 'lng' o None si wkb es None
#     """
#     from geoalchemy2.shape import to_shape
#     if wkb is None:
#         return None
#     point = to_shape(wkb)
#     return {"lat": point.y, "lng": point.x}


@router.get("/distance", description="""
Consulta la distancia y el tiempo estimado entre dos puntos usando Google Distance Matrix API.

**Parámetros:**
- `origin_lat`: Latitud de origen.
- `origin_lng`: Longitud de origen.
- `destination_lat`: Latitud de destino.
- `destination_lng`: Longitud de destino.

**Respuesta:**
Devuelve la distancia y el tiempo estimado entre los puntos especificados.
""")
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


@router.get("/nearby", description="""
Obtiene las solicitudes de viaje cercanas a un conductor en un radio de 5 km, incluyendo información de distancia, tiempo y datos del cliente.

**Parámetros:**
- `driver_lat`: Latitud del conductor.
- `driver_lng`: Longitud del conductor.

**Respuesta:**
Devuelve una lista de solicitudes cercanas con información de distancia, tiempo y datos del cliente.
""")
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


@router.post("/", response_model=ClientRequestResponse, status_code=status.HTTP_201_CREATED, description="""
Crea una nueva solicitud de viaje para un cliente.

**Parámetros:**
- `pickup_lat`: Latitud del punto de recogida.
- `pickup_lng`: Longitud del punto de recogida.
- `destination_lat`: Latitud del destino.
- `destination_lng`: Longitud del destino.
- `fare_offered`: Tarifa ofrecida.
- `pickup_description`: Descripción del punto de recogida (opcional).
- `destination_description`: Descripción del destino (opcional).

**Respuesta:**
Devuelve la solicitud de viaje creada con toda su información.
""")
def create_request(
    request: Request,
    request_data: ClientRequestCreate = Body(
        ...,
        example={
            "fare_offered": 20,
            "pickup_description": "Suba Bogotá",
            "destination_description": "Santa Rosita Engativa, Bogota",
            "pickup_lat": 4.718136,
            "pickup_lng": -74.073170,
            "destination_lat": 4.702468,
            "destination_lng": -74.109776
        }
    ),
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    try:
        user_id = request.state.user_id
        user_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id,
            UserHasRole.id_rol == "CLIENT"
        ).first()
        if not user_role or user_role.status != RoleStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail="El usuario no tiene el rol de cliente aprobado. No puede crear solicitudes."
            )
        db_obj = create_client_request(
            session, request_data, id_client=user_id)
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


@router.patch("/updateDriverAssigned", description="""
Asigna un conductor a una solicitud de viaje existente y actualiza el estado y la tarifa si se proporciona.

**Parámetros:**
- `id`: ID de la solicitud de viaje.
- `id_driver_assigned`: ID del conductor asignado.
- `fare_assigned`: Tarifa asignada (opcional).

**Respuesta:**
Devuelve un mensaje de éxito o error.
""")
def assign_driver(
    request_data: AssignDriverRequest = Body(
        ...,
        example={
            "id": 1,
            "id_driver_assigned": 2,
            "fare_assigned": 25
        }
    ),
    session: Session = Depends(get_session)
):
    """
    Asigna un conductor a una solicitud de viaje existente, cambia el estado a cualquiera de los estados
    "CREATED", "ACCEPTED", "ON_THE_WAY", "ARRIVED", "TRAVELLING", "FINISHED", "CANCELLED"
    y actualiza la tarifa si se proporciona.

    Args:
        request_data: Datos de la solicitud de asignación
        session: Sesión de base de datos
    Returns:
        Mensaje de éxito o error
    """
    try:
        return assign_driver_service(
            session, 
            request_data.id, 
            request_data.id_driver_assigned, 
            request_data.fare_assigned
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Error al asignar el conductor: {str(e)}"
        )


@router.patch("/updateStatus", description="""
Actualiza el estado de una solicitud de viaje existente.

**Parámetros:**
- `id_client_request`: ID de la solicitud de viaje.
- `status`: Nuevo estado a asignar.

**Respuesta:**
Devuelve un mensaje de éxito o error.
""")
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


@router.get("/{client_request_id}", description="""
Consulta el estado y la información detallada de una solicitud de viaje específica.

**Parámetros:**
- `client_request_id`: ID de la solicitud de viaje.

**Respuesta:**
Incluye el detalle de la solicitud, información del usuario, conductor y vehículo si aplica.
""")
def get_client_request_detail(
    client_request_id: int,
    session: Session = Depends(get_session)
):
    """
    Consulta el estado y la información detallada de una Client Request específica.
    """
    return get_client_request_detail_service(session, client_request_id)


@router.get("/by-status/{status}", description="""
Devuelve una lista de solicitudes de viaje filtradas por el estado enviado en el parámetro.

**Parámetros:**
- `status`: Estado por el cual filtrar las solicitudes.

**Respuesta:**
Devuelve una lista de solicitudes de viaje con el estado especificado.
""")
def get_client_requests_by_status(
    status: str = Path(..., description="Estado por el cual filtrar las solicitudes. Debe ser uno de: CREATED, ACCEPTED, ON_THE_WAY, ARRIVED, TRAVELLING, FINISHED, CANCELLED"),
    session: Session = Depends(get_session)
):
    """
    Devuelve una lista de client_request filtrados por el estatus enviado en el parámetro.
    """
    # Validar que el status sea uno de los permitidos
    if status not in StatusEnum.__members__:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Debe ser uno de: {', '.join(StatusEnum.__members__.keys())}"
        )
    return get_client_requests_by_status_service(session, status)


@router.patch("/updateClientRating", description="""
Actualiza la calificación del cliente para una solicitud de viaje. Solo el conductor asignado puede calificar al cliente.

**Parámetros:**
- `id_client_request`: ID de la solicitud de viaje.
- `client_rating`: Nueva calificación del cliente.

**Respuesta:**
Devuelve un mensaje de éxito o error.
""")
def update_client_rating(
    request: Request,
    id_client_request: int = Body(...,
                                  description="ID de la solicitud de viaje"),
    client_rating: float = Body(...,
                                description="Nueva calificación del cliente"),
    session: Session = Depends(get_session)
):
    """
    Actualiza la calificación del cliente para una solicitud de viaje.
    Solo el conductor asignado puede calificar al cliente.
    """
    user_id = request.state.user_id
    return update_client_rating_service(session, id_client_request, client_rating, user_id)


@router.patch("/updateDriverRating", description="""
Actualiza la calificación del conductor para una solicitud de viaje. Solo el cliente puede calificar al conductor.

**Parámetros:**
- `id_client_request`: ID de la solicitud de viaje.
- `driver_rating`: Nueva calificación del conductor.

**Respuesta:**
Devuelve un mensaje de éxito o error.
""")
def update_driver_rating(
    request: Request,
    id_client_request: int = Body(...,
                                  description="ID de la solicitud de viaje"),
    driver_rating: float = Body(...,
                                description="Nueva calificación del conductor"),
    session: Session = Depends(get_session)
):
    """
    Actualiza la calificación del conductor para una solicitud de viaje.
    Solo el cliente puede calificar al conductor.
    """
    user_id = request.state.user_id
    return update_driver_rating_service(session, id_client_request, driver_rating, user_id)

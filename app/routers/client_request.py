from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
import requests
from app.core.config import settings
from app.core.db import get_session
from app.models.client_request import ClientRequest, ClientRequestCreate
from app.services.client_requests_service import create_client_request
import traceback
from geoalchemy2.shape import to_shape
from pydantic import BaseModel

router = APIRouter(prefix="/client-request", tags=["client-request"])

# Modelo de respuesta personalizado


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
    pickup_position: dict | None = None
    destination_position: dict | None = None
    created_at: str
    updated_at: str

# Utilidad para convertir WKBElement a dict lat/lng


def wkb_to_coords(wkb):
    if wkb is None:
        return None
    point = to_shape(wkb)
    return {"lat": point.y, "lng": point.x}


@router.get("/distance")
def get_time_and_distance(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float
):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{destination_lat},{destination_lng}",
        "units": "metric",
        "key": settings.GOOGLE_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "message": f"Error en el API de Google Distance Matrix: {response.status_code}"}
            )
        data = response.json()
        if data.get("status") != "OK":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}"}
            )
        return data
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)}
        )


@router.get("/distance/prueba")
def get_time_and_distance_prueba():
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "Boston, Massachusetts, EE. UU.",
        "destinations": "Nueva York, EE. UU.",
        "units": "metric",
        "key": settings.GOOGLE_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "message": f"Error en el API de Google Distance Matrix: {response.status_code}"}
            )
        data = response.json()
        if data.get("status") != "OK":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}"}
            )
        return data
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)}
        )


@router.post("/", response_model=ClientRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(request_data: ClientRequestCreate, request: Request, session: requests.Session = Depends(get_session)):
    try:
        user_id = request.state.user_id
        if hasattr(request_data, 'id_client'):
            request_data.id_client = user_id
        print(f"DEBUG - id_client (user_id): {request_data.id_client}")
        db_obj = create_client_request(session, request_data)
        # Serializar los campos geográficos
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
            status_code=500, detail=f"Error al crear la solicitud de viaje: {str(e)}")

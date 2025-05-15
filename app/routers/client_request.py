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
    update_status_service
)
from sqlalchemy.orm import Session
import traceback
from pydantic import BaseModel

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
    from geoalchemy2.shape import to_shape
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
    try:
        return get_time_and_distance_service(origin_lat, origin_lng, destination_lat, destination_lng)
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(e)})


@router.get("/distance/prueba")
def get_time_and_distance_prueba():
    try:
        return get_time_and_distance_prueba_service()
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(e)})


@router.get("/nearby")
def get_nearby_client_requests(
    driver_lat: float,
    driver_lng: float,
    session=Depends(get_session)
):
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
def create_request(request_data: ClientRequestCreate, request: Request, session: Session = Depends(get_session)):
    try:
        user_id = request.state.user_id
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
            status_code=500, detail=f"Error al crear la solicitud de viaje: {str(e)}")


@router.patch("/updateDriverAssigned")
def assign_driver(
    id: int = Body(...),
    id_driver_assigned: int = Body(...),
    fare_assigned: float = Body(None),
    session: Session = Depends(get_session)
):
    try:
        return assign_driver_service(session, id, id_driver_assigned, fare_assigned)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al asignar conductor: {str(e)}")


@router.patch("/updateStatus")
def update_status(
    id_client_request: int = Body(...),
    status: str = Body(...),
    session: Session = Depends(get_session)
):
    try:
        return update_status_service(session, id_client_request, status)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar el status: {str(e)}")

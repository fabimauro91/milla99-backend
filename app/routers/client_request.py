from fastapi import APIRouter, HTTPException, status, Depends, Request, Query, Body
from fastapi.responses import JSONResponse
import requests
from app.core.config import settings
from app.core.db import get_session
from app.models.client_request import ClientRequest, ClientRequestCreate
from app.models.user import User
from app.services.client_requests_service import create_client_request
import traceback
from geoalchemy2.shape import to_shape
from pydantic import BaseModel
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func, and_, text
from geoalchemy2.functions import ST_Distance_Sphere
from datetime import datetime, timedelta, timezone
import json

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


@router.get("/{driver_lat}/{driver_lng}")
def get_nearby_client_requests(
    driver_lat: float,
    driver_lng: float,
    session=Depends(get_session)
):
    try:
        print(
            f"DEBUG - Buscando solicitudes cercanas para coordenadas: {driver_lat}, {driver_lng}")
        # Crear el punto del conductor
        driver_point = func.ST_GeomFromText(
            f'POINT({driver_lng} {driver_lat})', 4326)
        # Hora límite (últimos 30 minutos)
        time_limit = datetime.now(timezone.utc) - timedelta(minutes=30)
        print(f"DEBUG - Hora límite: {time_limit}")

        # Consulta ORM
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
            .having(text("distance < 5000"))
        )

        print("DEBUG - Query SQL:",
              str(base_query.statement.compile(compile_kwargs={"literal_binds": True})))

        print("DEBUG - Ejecutando consulta...")
        results = []
        try:
            query_results = base_query.all()
            print(f"DEBUG - Número de resultados raw: {len(query_results)}")

            for row in query_results:
                try:
                    cr, full_name, country_code, phone_number, distance, time_difference = row
                    print(
                        f"DEBUG - Procesando fila: distance={distance}, time_difference={time_difference}")

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
                except Exception as e:
                    print(
                        f"DEBUG - Error procesando fila individual: {str(e)}")
                    print(f"DEBUG - Datos de la fila: {row}")
                    continue

            print(f"DEBUG - Número de resultados procesados: {len(results)}")

            results_json = []
            pickup_positions = []
            for result in results:
                results_json.append(result)
                pickup_positions.append(
                    f"{result['pickup_position']['lat']},{result['pickup_position']['lng']}"
                )

            origins = f"{driver_lat},{driver_lng}"
            destinations = '|'.join(pickup_positions)
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
                results_json[index]['google_distance_matrix'] = element

            return JSONResponse(content=results_json, status_code=200)

        except Exception as e:
            print(f"DEBUG - Error ejecutando consulta: {str(e)}")
            print(
                f"DEBUG - Traceback de la consulta: {traceback.format_exc()}")
            raise

    except Exception as e:
        print(f"DEBUG - Error general: {str(e)}")
        print(f"DEBUG - Traceback completo: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Error al buscar solicitudes cercanas: {str(e)}"
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


@router.patch("/updateDriverAssigned")
def assign_driver(
    id: int = Body(...),
    id_driver_assigned: int = Body(...),
    fare_assigned: float = Body(None),
    session: Session = Depends(get_session)
):
    try:
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
        client_request = session.query(ClientRequest).filter(
            ClientRequest.id == id_client_request).first()
        if not client_request:
            raise HTTPException(
                status_code=404, detail="Solicitud no encontrada")
        client_request.status = status
        client_request.updated_at = datetime.utcnow()
        session.commit()
        return {"success": True, "message": "Status actualizado correctamente"}
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar el status: {str(e)}")

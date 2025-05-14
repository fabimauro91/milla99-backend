from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import requests
from app.core.config import settings

router = APIRouter(prefix="/client-request", tags=["client-request"])

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
                content={"message": f"Error en el API de Google Distance Matrix: {response.status_code}"}
            )
        data = response.json()
        if data.get("status") != "OK":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}"}
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
                content={"message": f"Error en el API de Google Distance Matrix: {response.status_code}"}
            )
        data = response.json()
        if data.get("status") != "OK":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}"}
            )
        return data
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)}
        ) 
    

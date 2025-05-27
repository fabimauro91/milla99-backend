from fastapi import APIRouter, status, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any
# Importación absoluta
from app.services.config_service_value import ConfigServiceValueService
from app.core.db import SessionDep  # Importación absoluta
from app.models.config_service_value import VehicleTypeConfigurationCreate, FareCalculationResponse
from app.core.config import settings

router = APIRouter(prefix="/distance-value", tags=["distance-value"])


# @router.post("/", response_model=VehicleTypeConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_config_service_value(
    data: VehicleTypeConfigurationCreate,
    db: SessionDep
):
    """
    Crea un nuevo registro de configuración de tipo de vehículo
    """
    try:
        service = ConfigServiceValueService(db)
        result = service.create_config_service_value(
            km_value=data.km_value,
            min_value=data.min_value,
            tarifa_value=data.tarifa_value,
            weight_value=data.weight_value
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=FareCalculationResponse, description="""
Calcula la tarifa recomendada para un viaje según el tipo de vehículo y la distancia entre dos puntos.

**Parámetros:**
- `type_service_id`: ID del tipo de vehículo.
- `origin_lat`: Latitud de origen.
- `origin_lng`: Longitud de origen.
- `destination_lat`: Latitud de destino.
- `destination_lng`: Longitud de destino.

**Respuesta:**
Devuelve la tarifa recomendada, las direcciones de origen y destino, la distancia y la duración estimada del viaje.
""")
async def calculate_fare_unique(
    session: SessionDep,
    type_service_id: int = Query(..., description="ID del tipo de servicio"),
    origin_lat: float = Query(..., description="Latitud de origen"),
    origin_lng: float = Query(..., description="Longitud de origen"),
    destination_lat: float = Query(..., description="Latitud de destino"), 
    destination_lng: float = Query(..., description="Longitud de destino"),
):
    try:
        service = ConfigServiceValueService(session)
        # 1. Llama a Google Distance Matrix
        google_data = service.get_google_distance_data(
            origin_lat,
            origin_lng,
            destination_lat,
            destination_lng,
            settings.GOOGLE_API_KEY
        )
        # 2. Calcula la tarifa
        result = await service.calculate_total_value(type_service_id, google_data)

        if result is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "No se pudo calcular la tarifa"}
            )

        return result

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error en el servidor: {str(e)}"}
        )

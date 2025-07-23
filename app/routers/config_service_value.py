from fastapi import APIRouter, status, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
# Importación absoluta
from app.services.config_service_value_service import ConfigServiceValueService
from app.core.db import SessionDep  # Importación absoluta
from app.models.config_service_value import VehicleTypeConfigurationCreate, FareCalculationResponse
from app.core.config import settings
from app.core.dependencies.auth import get_current_user

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
Calcula la tarifa recomendada para un viaje según el tipo de vehículo y la distancia entre dos puntos. (toma id_user desde el token)

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
    request: Request,
    session: SessionDep,
    type_service_id: int = Query(..., description="ID del tipo de servicio"),
    origin_lat: float = Query(..., description="Latitud de origen"),
    origin_lng: float = Query(..., description="Longitud de origen"),
    destination_lat: float = Query(..., description="Latitud de destino"),
    destination_lng: float = Query(..., description="Longitud de destino"),
    current_user=Depends(get_current_user)
):
    try:
        user_id = request.state.user_id
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


@router.post("/multiple-stops", response_model=FareCalculationResponse, description="""
Calcula la tarifa recomendada para un viaje con múltiples paradas intermedias usando Google Directions API.

**Ventajas:**
- ✅ Calcula ruta optimizada (no solo suma segmentos)
- ✅ Considera tráfico real
- ✅ Calcula distancia y tiempo total precisos
- ✅ Una sola llamada a la API

**Parámetros:**
- `type_service_id`: ID del tipo de vehículo
- `origin_lat`: Latitud de origen
- `origin_lng`: Longitud de origen  
- `destination_lat`: Latitud de destino
- `destination_lng`: Longitud de destino
- `intermediate_stops`: Lista de paradas intermedias (opcional)

**Ejemplo:**
```json
{
  "type_service_id": 1,
  "origin_lat": 4.650788,
  "origin_lng": -74.089519,
  "destination_lat": 4.5981,
  "destination_lng": -74.0758,
  "intermediate_stops": [
    {
      "latitude": 4.670000,
      "longitude": -74.090000,
      "description": "Banco"
    },
    {
      "latitude": 4.680000,
      "longitude": -74.085000,
      "description": "Paquetería"
    }
  ]
}
```

**Respuesta:**
Devuelve la tarifa recomendada basada en la ruta completa optimizada.
""")
async def calculate_fare_multiple_stops_optimized(
    request: Request,
    session: SessionDep,
    data: dict,
    current_user=Depends(get_current_user)
):
    try:
        user_id = request.state.user_id
        service = ConfigServiceValueService(session)

        # Validar parámetros requeridos
        required_fields = ["type_service_id", "origin_lat",
                           "origin_lng", "destination_lat", "destination_lng"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo requerido faltante: {field}"
                )

        # Extraer datos del body
        type_service_id = data["type_service_id"]
        origin_lat = data["origin_lat"]
        origin_lng = data["origin_lng"]
        destination_lat = data["destination_lat"]
        destination_lng = data["destination_lng"]
        intermediate_stops = data.get("intermediate_stops", [])

        # Usar el servicio para calcular la tarifa
        result = await service.calculate_fare_multiple_stops(
            type_service_id=type_service_id,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            intermediate_stops=intermediate_stops,
            api_key=settings.GOOGLE_API_KEY
        )

        return result

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error en el servidor: {str(e)}"}
        )

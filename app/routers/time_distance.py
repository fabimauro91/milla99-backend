from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session 
from typing import Dict, Any
from app.services.time_distance_service import TimeDistanceValueService  # Importación absoluta
from app.core.db import SessionDep  # Importación absoluta
from app.models.time_distance_value import TimeDistanceValueCreate, TimeDistanceValueUpdate, TimeDistanceValueResponse,CalculateFareRequest,FareCalculationResponse
from app.core.config import settings

router = APIRouter(prefix="/time-distance", tags=["time-distance"])


# @router.post("/", response_model=TimeDistanceValueResponse, status_code=status.HTTP_201_CREATED)
# async def create_time_distance(
#     data: TimeDistanceValueCreate,
#     db: SessionDep
# ):
#     """
#     Crea un nuevo registro de tiempo y distancia
#     """
#     try:
#         service = TimeDistanceValueService(db)
#         result = service.create_time_distance_value(
#             km_value=data.km_value,
#             min_value=data.min_value,
#             tarifa_value=data.tarifa_value,
#             weight_value=data.weight_value
#         )
#         return result
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
    

@router.patch("/{id}", response_model=TimeDistanceValueResponse)
async def update_time_distance(
    id: int,
    data: TimeDistanceValueUpdate,
    db: SessionDep
):
    """
    Actualiza un registro existente
    """
    try:
        service = TimeDistanceValueService(db)
        # Convertir el modelo Pydantic a diccionario y eliminar valores None
        update_data = {k: v for k, v in data.dict().items() if v is not None}

        result = service.update_time_distance_value(id, update_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado"
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )   


@router.post("/calculate-fare", response_model=FareCalculationResponse)
async def calculate_fare_unique(
    request: CalculateFareRequest,
    db: SessionDep
):
    try:
        service = TimeDistanceValueService(db)
        # 1. Llama a Google Distance Matrix
        google_data = service.get_google_distance_data(
            request.origin_lat,
            request.origin_lng,
            request.destination_lat,
            request.destination_lng,
            settings.GOOGLE_API_KEY
        )
        # 2. Calcula la tarifa
        result = await service.calculate_total_value(request.fare_id, google_data)

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
from fastapi import APIRouter, status, HTTPException, Query
from typing import Optional
from app.services.config_service_value_service import ConfigServiceValueService  # Importación absoluta
from app.core.db import SessionDep  # Importación absoluta
from app.models.config_service_value import  VehicleTypeConfigurationUpdate, VehicleTypeConfigurationResponse

router = APIRouter(prefix="/config-service-value", tags=["ADMIN: config-service-value"])


@router.get("/{vehicle_type_id}", response_model=VehicleTypeConfigurationResponse)
async def update_config_service_value(
    db: SessionDep,
    vehicle_type_id: int,
    km_value: Optional[float] = Query(None, description="Valor por kilómetro"),
    min_value: Optional[float] = Query(None, description="Valor por minuto"),
    tarifa_value: Optional[float] = Query(None, description="Valor de tarifa base"),
    weight_value: Optional[float] = Query(None, description="Valor de peso"),
    
):
    """
    Actualiza la configuración de tarifas  usando el ID de VehicleType.

    **Parámetros:**
    - `vehicle_type_id`: ID único del tipo de vehiculo.
    - `km_value`: Nuevo valor por kilometro a modificar, es opcional. 
    - `min_value`: Nuevo valor por minuto a modificar, es opcional. 
    - `tarifa_value`: Nuevo valor en tarifa minima a modificar, es opcional.  
    - `weight_value`: Nuevo valor peso de carga a modificar, es opcional.  

    **Respuesta:**
    Devuelve el vehicle type configuration modificado.
    """
    try:
        service = ConfigServiceValueService(db)

        # Crear diccionario con los parámetros no nulos
        update_data = {}
        if km_value is not None:
            update_data["km_value"] = km_value
        if min_value is not None:
            update_data["min_value"] = min_value
        if tarifa_value is not None:
            update_data["tarifa_value"] = tarifa_value
        if weight_value is not None:
            update_data["weight_value"] = weight_value

        # Si no hay datos para actualizar, informar al usuario
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar"
            )

        result = service.update_by_vehicle_type_id(vehicle_type_id, update_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado para ese tipo de vehículo"
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
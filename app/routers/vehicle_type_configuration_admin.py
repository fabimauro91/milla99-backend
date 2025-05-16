from fastapi import APIRouter, status, HTTPException

from app.services.vehicle_type_configuration_service import VehicleTypeConfigurationService  # Importación absoluta
from app.core.db import SessionDep  # Importación absoluta
from app.models.vehicle_type_configuration import  VehicleTypeConfigurationUpdate, VehicleTypeConfigurationResponse

router = APIRouter(prefix="/vehicle-type-configuration", tags=["ADMIN: vehicle-type-configuration"])


@router.patch("/{vehicle_type_id}", response_model=VehicleTypeConfigurationResponse)
async def update_vehicle_type_configuration(
    vehicle_type_id: int,
    data: VehicleTypeConfigurationUpdate,
    db: SessionDep
):
    """
    Actualiza la configuración de un tipo de vehículo usando el ID de VehicleType.
    """
    try:
        service = VehicleTypeConfigurationService(db)
        update_data = {k: v for k, v in data.dict().items() if v is not None}
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
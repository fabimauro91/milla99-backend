from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.core.dependencies.admin_auth import get_current_admin
from app.core.db import SessionDep
from app.services.statistics_service import StatisticsService

router = APIRouter(
    prefix="/admin/drivers",
    tags=["ADMIN - Drivers Management"],
    dependencies=[Depends(get_current_admin)]
)


@router.post("/batch-check-suspensions", response_model=Dict[str, Any])
def batch_check_driver_suspensions(
    session: SessionDep
):
    """
    Verifica y reactiva automáticamente a todos los conductores suspendidos que ya cumplieron su tiempo de suspensión.

    **SOLO PARA ADMINISTRADORES**

    **¿Qué hace este endpoint?**
    - Obtiene TODOS los conductores suspendidos
    - Para cada conductor, verifica si han pasado los 7 días de suspensión  
    - Si han pasado los días, los reactiva automáticamente:
      - `suspension = False`
      - `status = APPROVED` 
      - Elimina todas sus cancelaciones registradas
    - Si NO han pasado los días, los deja suspendidos

    **Respuesta:**
    Devuelve estadísticas detalladas de la operación con información de:
    - Total de conductores suspendidos encontrados
    - Cuántos fueron reactivados
    - Cuántos siguen suspendidos
    - Detalles específicos de cada caso

    **Casos de uso:**
    - Ejecutar manualmente desde el admin
    - Configurar como tarea programada (cron job)
    - Verificación masiva de suspensiones

    **Ejemplo de respuesta:**
    ```json
    {
        "success": true,
        "message": "Verificación masiva de suspensiones completada",
        "data": {
            "success": true,
            "total_suspended_drivers": 5,
            "suspensions_lifted": 2,
            "still_suspended": 3,
            "lifted_details": [
                {
                    "driver_id": "uuid1",
                    "message": "Suspensión levantada automáticamente..."
                }
            ],
            "still_suspended_details": [
                {
                    "driver_id": "uuid2",
                    "message": "El conductor aún está suspendido. Tiempo restante: 2 días"
                }
            ]
        }
    }
    ```
    """
    try:
        service = StatisticsService(session)
        result = service.batch_check_all_suspended_drivers()

        return {
            "success": True,
            "message": "Verificación masiva de suspensiones completada",
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar suspensiones masivamente: {str(e)}"
        )

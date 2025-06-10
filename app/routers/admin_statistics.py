from fastapi import APIRouter, Depends, Query, status
from typing import Dict, Any, Optional
from datetime import date
from uuid import UUID

from app.core.dependencies.admin_auth import get_current_admin
from app.core.db import SessionDep
from app.services.statistics_service import StatisticsService

router = APIRouter(
    prefix="/admin/statistics",
    tags=["ADMIN - Statistics"],
    dependencies=[Depends(get_current_admin)]
)


@router.get("/summary", response_model=Dict[str, Any])
def get_admin_statistics_summary(
    session: SessionDep,
    start_date: Optional[date] = Query(
        None, description="Fecha de inicio para el rango de estadísticas (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(
        None, description="Fecha de fin para el rango de estadísticas (YYYY-MM-DD)"),
    service_type_id: Optional[int] = Query(
        None, description="ID del tipo de servicio para filtrar (ej. 1 para Carro, 2 para Motocicleta)"),
    driver_id: Optional[UUID] = Query(
        None, description="ID del conductor para filtrar estadísticas por conductor"),
):
    """
    Obtiene un resumen de estadísticas administrativas.

    - **`start_date`**: Fecha de inicio del período para las estadísticas.
    - **`end_date`**: Fecha de fin del período para las estadísticas.
    - **`service_type_id`**: Filtra las estadísticas por un tipo de servicio específico.
    - **`driver_id`**: Filtra las estadísticas para un conductor específico.

    **Respuesta:**
    Retorna un objeto JSON con diversas métricas sobre servicios, finanzas, usuarios y más.
    """
    service = StatisticsService(session)
    return service.get_summary_statistics(
        start_date=start_date,
        end_date=end_date,
        service_type_id=service_type_id,
        # Convertir UUID a str para el servicio
        driver_id=str(driver_id) if driver_id else None
    )

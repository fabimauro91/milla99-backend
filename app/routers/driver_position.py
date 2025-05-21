from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.driver_position import DriverPositionCreate, DriverPositionRead
from app.core.db import get_session
from app.services.driver_position_service import DriverPositionService
from app.models.project_settings import ProjectSettings

router = APIRouter(prefix="/drivers-position", tags=["drivers-position"])

@router.post(
    "/",
    response_model=DriverPositionRead,
    status_code=status.HTTP_201_CREATED,
    description="""
Registra o actualiza la posición actual de un conductor en el sistema.

**Parámetros:**
- `id_driver`: ID único del conductor. 
- `lat`: Latitud donde se encuentra el conductor. 
- `lng`: Longitud donde se encuentra el conductor. 

**Respuesta:**
Devuelve la posición registrada del conductor.
"""
)
def create_driver_position(
    data: DriverPositionCreate,
    session: Session = Depends(get_session)
):
    service = DriverPositionService(session)
    obj = service.create_driver_position(data)
    return DriverPositionRead.from_orm_with_point(obj) 

@router.get(
    "/{id_driver}",
    response_model=DriverPositionRead,
    description="""
Devuelve la posición actual de un conductor dado su ID.

**Parámetros:**
- `id_driver`: ID único del conductor.

**Respuesta:**
Incluye la latitud, longitud y (si aplica) la distancia al punto de búsqueda.
"""
)
def get_driver_position(
    id_driver: int,
    session: Session = Depends(get_session)
):
    service = DriverPositionService(session)
    obj = service.get_driver_position(id_driver)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conductor no encontrado o sin posición registrada")
    return DriverPositionRead.from_orm_with_point(obj) 

@router.delete(
    "/{id_driver}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="""
Elimina la posición registrada de un conductor dado su ID.

**Parámetros:**
- `id_driver`: ID único del conductor.

**Respuesta:**
No retorna contenido si la eliminación fue exitosa.
"""
)
def delete_driver_position(
    id_driver: int,
    session: Session = Depends(get_session)
):
    service = DriverPositionService(session)
    success = service.delete_driver_position(id_driver)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conductor no encontrado o sin posición registrada") 


@router.get(
    "/nearby",
    response_model=List[DriverPositionRead],
    description="""
Devuelve una lista de conductores cercanos a una ubicación dada.

**Parámetros:**
- `lat`: Latitud del punto de búsqueda.
- `lng`: Longitud del punto de búsqueda.
- `max_distance`: Radio máximo de búsqueda en kilómetros (opcional, por defecto 5 km).

**Respuesta:**
Incluye la posición y la distancia (en kilómetros) de cada conductor respecto al punto de búsqueda.

**Notas:**
- Si no se especifica `max_distance`, se usa un radio de 5 km.
- El resultado está ordenado del conductor más cercano al más lejano.
"""
)
def get_nearby_drivers(
    lat: float = Query(..., description="Latitud del punto de búsqueda"),
    lng: float = Query(..., description="Longitud del punto de búsqueda"),
    max_distance: Optional[float] = Query(None, description="Distancia máxima en kilómetros (por defecto: valor de configuración)"),
    session: Session = Depends(get_session)
):
    # Si no se especifica max_distance, obtener el valor de ProjectSettings id=1
    if max_distance is None:
        setting = session.get(ProjectSettings, 1)
        if setting is not None:
            try:
                max_distance = float(setting.value)
            except ValueError:
                max_distance = 5  # fallback si el valor no es convertible
        else:
            max_distance = 5  # fallback si no existe el setting

    service = DriverPositionService(session)
    return service.get_nearby_drivers(lat=lat, lng=lng, max_distance_km=max_distance)
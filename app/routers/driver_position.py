from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Security
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.driver_position import DriverPositionCreate, DriverPositionRead
from app.core.db import get_session
from app.services.driver_position_service import DriverPositionService
from app.models.project_settings import ProjectSettings
from uuid import UUID
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.models.driver_info import DriverInfo
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.core.dependencies.auth import get_current_user

router = APIRouter(prefix="/drivers-position", tags=["drivers-position"])

bearer_scheme = HTTPBearer()


@router.post(
    "/",
    response_model=DriverPositionRead,
    status_code=status.HTTP_201_CREATED,
    description="""
Registra o actualiza la posición actual del conductor autenticado (se toma el user_id desde el token).

**Parámetros:**
- `lat`: Latitud donde se encuentra el conductor. 
- `lng`: Longitud donde se encuentra el conductor. 

**Respuesta:**
Devuelve la posición registrada del conductor.
"""
)
def create_driver_position(
    request: Request,
    data: DriverPositionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Obtener el user_id desde el token
    user_id = request.state.user_id

    # Validar que el usuario tenga el rol DRIVER aprobado
    driver_role = session.query(UserHasRole).filter(
        UserHasRole.id_user == user_id,
        UserHasRole.id_rol == "DRIVER",
        UserHasRole.status == RoleStatus.APPROVED
    ).first()

    if not driver_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene el rol de conductor aprobado"
        )

    service = DriverPositionService(session)
    obj = service.create_driver_position(data, user_id)
    return DriverPositionRead.from_orm_with_point(obj)


@router.get(
    "/me",
    response_model=DriverPositionRead,
    description="""
Devuelve la posición actual del conductor autenticado (toma el user_id desde el token).

**Respuesta:**
Incluye la latitud, longitud y (si aplica) la distancia al punto de búsqueda.
"""
)
def get_driver_position(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Obtener el user_id desde el token
    user_id = request.state.user_id
    # Buscar el driver_info correspondiente a este usuario
    driver_info = session.query(DriverInfo).filter(
        DriverInfo.user_id == user_id).first()
    if not driver_info:
        raise HTTPException(
            status_code=404, detail="No se encontró información de conductor para este usuario.")
    id_driver = driver_info.user_id
    # Usar el servicio existente para obtener la posición
    service = DriverPositionService(session)
    obj = service.get_driver_position(id_driver)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conductor no encontrado o sin posición registrada")
    return DriverPositionRead.from_orm_with_point(obj)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    description="""
Elimina la posición registrada del conductor autenticado (toma el user_id desde el token).

**Respuesta:**
No retorna contenido si la eliminación fue exitosa.
"""
)
def delete_my_driver_position(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Obtener el user_id desde el token
    user_id = request.state.user_id
    print(f"user_id: {user_id}")
    # Buscar el driver_info correspondiente a este usuario
    driver_info = session.query(DriverInfo).filter(
        DriverInfo.user_id == user_id).first()
    if not driver_info:
        raise HTTPException(
            status_code=404, detail="No se encontró información de conductor para este usuario.")
    id_driver = driver_info.user_id
    # Usar el servicio existente para eliminar la posición
    service = DriverPositionService(session)
    success = service.delete_driver_position(id_driver)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conductor no encontrado o sin posición registrada")
    # No retorna contenido si la eliminación fue exitosa


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
    max_distance: Optional[float] = Query(
        None, description="Distancia máxima en kilómetros (por defecto: valor de configuración)"),
    session: Session = Depends(get_session)
):
    # Si no se especifica max_distance, obtener el valor de ProjectSettings id=1
    if max_distance is None:
        setting = session.get(ProjectSettings, 1)
        if setting is not None:
            try:
                max_distance = float(setting.driver_dist)
            except ValueError:
                max_distance = 5  # fallback si el valor no es convertible
        else:
            max_distance = 5  # fallback si no existe el setting

    service = DriverPositionService(session)
    return service.get_nearby_drivers(lat=lat, lng=lng, max_distance_km=max_distance)


@router.get(
    "/by-client-request/{id_client_request}",
    description="""
    Devuelve la lista de conductores con posición actual compatibles con el tipo de servicio de la solicitud.
    """
)
def get_drivers_by_client_request(
    id_client_request: UUID,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    user_id = request.state.user_id
    # Consultar el rol real del usuario en la base de datos
    user_has_role = session.query(UserHasRole).filter(
        UserHasRole.id_user == user_id,
        UserHasRole.status == RoleStatus.APPROVED
    ).first()
    if not user_has_role:
        print(f"[ERROR] El usuario {user_id} no tiene rol aprobado")
        raise HTTPException(
            status_code=403, detail="No tiene rol asignado o aprobado")
    user_role = user_has_role.id_rol  # 'DRIVER' o 'CLIENT'
    print(f"[DEBUG] user_id: {user_id}, user_role: {user_role}")
    service = DriverPositionService(session)
    return service.get_nearby_drivers_by_client_request(id_client_request, user_id, user_role)

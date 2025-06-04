from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies.admin_auth import get_current_admin
from ..core.db import SessionDep
from app.models.project_settings import ProjectSettings, ProjectSettingsUpdate, ProjectSettingsCreate
from app.services.project_settings_service import (
    update_project_settings_service,
    get_project_settings_service,
    create_project_settings_service
)

router = APIRouter(prefix="/project-settings", tags=["ADMIN: Project Settings"])


@router.get("/", response_model=ProjectSettings, description="""
Obtiene la configuración actual del proyecto.
""")
def get_project_settings(session: SessionDep, current_admin=Depends(get_current_admin)):
    """
    Obtiene la configuración actual del proyecto.
    """
    return get_project_settings_service(session)




@router.post("/", response_model=ProjectSettings, description="""
Crea la configuración inicial del proyecto.

**Nota:** Solo se puede crear una configuración. Para modificar, usa el endpoint PUT.
""")
def create_project_settings(session: SessionDep,
    settings_data: ProjectSettingsCreate,current_admin=Depends(get_current_admin)
):
    """
    Crea la configuración inicial del proyecto.
    """
    return create_project_settings_service(session, settings_data)



@router.put("/", response_model=ProjectSettings, description="""
Actualiza la configuración del proyecto.

**Parámetros:**
- Solo envía los campos que quieres actualizar
- Los campos no enviados mantendrán su valor actual

**Ejemplo:**
```json
{
    "driver_dist": "10.5",
    "referral_1": "5.0",
    "company": "15.0"
}
""")
def update_project_settings(session: SessionDep,
settings_data: ProjectSettingsUpdate,current_admin=Depends(get_current_admin)
):
    """
    Actualiza la configuración del proyecto.
    Solo actualiza los campos proporcionados.
    """
    return update_project_settings_service(session, settings_data)
from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form, Request, Depends
from app.services.upload_service import save_uploaded_file, FIELD_TO_CATEGORY
from app.services.driver_service import DriverService
from app.core.db import get_session
from sqlmodel import Session, select
from typing import Optional
from app.models.driver import Driver

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/driver-doc")
async def upload_driver_document(
    request: Request,
    file: UploadFile = File(...),
    field: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """
    Sube un archivo y actualiza el campo correspondiente en el modelo Driver.
    """
    user_id = request.state.user_id
    # Obtener el driver asociado al usuario autenticado
    driver = session.exec(select(Driver).where(
        Driver.user_id == user_id)).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    # Aquí usas el mapeo que ya tienes
    category = FIELD_TO_CATEGORY.get(field, "drivers")
    # Subir el archivo
    url = save_uploaded_file(file, category)
    # Actualizar el campo correspondiente
    driver_service = DriverService(session)
    driver_service.update_driver_document(driver.id, field, url)
    return {
        "message": f"{field} actualizado exitosamente",
        "url": url,
        "user_id": user_id,
        "driver_id": driver.id,
        "field": field,
        "description": description
    }

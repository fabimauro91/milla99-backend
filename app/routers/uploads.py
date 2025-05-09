from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form, Request, Depends
from app.utils.uploads import uploader
from app.core.db import get_session
from sqlmodel import Session, select
from typing import Optional
from app.models.driver import Driver
from app.models.driver_info import DriverInfo
from app.models.driver_documents import DriverDocuments

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
    Sube un archivo y actualiza el campo correspondiente en el modelo DriverDocuments.
    """
    user_id = request.state.user_id

    # Obtener el driver asociado al usuario autenticado
    driver = session.exec(select(Driver).where(
        Driver.user_id == user_id)).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Obtener o crear DriverDocuments
    driver_documents = session.exec(
        select(DriverDocuments).where(
            DriverDocuments.driver_info_id == driver.driver_info_id)
    ).first()

    if not driver_documents:
        driver_documents = DriverDocuments(
            driver_info_id=driver.driver_info_id)
        session.add(driver_documents)
        session.commit()
        session.refresh(driver_documents)

    # Mapeo de campos a tipos de documento y subcarpetas
    FIELD_MAPPING = {
        "property_card_front": ("property_card", "front"),
        "property_card_back": ("property_card", "back"),
        "license_front": ("license", "front"),
        "license_back": ("license", "back"),
        "soat": ("soat", None),
        "vehicle_technical_inspection": ("technical_inspection", None)
    }

    if field not in FIELD_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field. Must be one of: {', '.join(FIELD_MAPPING.keys())}"
        )

    document_type, subfolder = FIELD_MAPPING[field]

    # Subir el archivo
    relative_path = await uploader.save_driver_document(
        file=file,
        driver_id=driver.id,
        document_type=document_type,
        subfolder=subfolder
    )

    # Actualizar el campo correspondiente en DriverDocuments
    setattr(driver_documents, f"{field}_url", relative_path)
    session.add(driver_documents)
    session.commit()
    session.refresh(driver_documents)

    return {
        "message": f"{field} actualizado exitosamente",
        "url": uploader.get_file_url(relative_path),
        "user_id": user_id,
        "driver_id": driver.id,
        "field": field,
        "description": description
    }


@router.post("/driver-info-selfie")
async def upload_driver_info_selfie(
    file: UploadFile = File(...),
    user_id: int = Form(...)
):
    """
    Sube la selfie de DriverInfo antes de crear el Driver.
    Guarda la selfie en static/uploads/driver_info/{user_id}/selfie/
    """
    # Guardar la selfie en una carpeta específica para driver_info
    document_type = "selfie"
    driver_info_path = f"driver_info/{user_id}/{document_type}"
    # Generar nombre único para el archivo
    filename = uploader._generate_unique_filename(file.filename)
    # Crear la ruta completa
    from pathlib import Path
    Path(
        f"static/uploads/{driver_info_path}").mkdir(parents=True, exist_ok=True)
    file_path = f"static/uploads/{driver_info_path}/{filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    # Retornar la URL relativa
    relative_url = f"/{driver_info_path}/{filename}"
    return {"url": relative_url}

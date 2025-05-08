from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form, Depends
from app.services.upload_service import save_uploaded_file, UploadCategory
from typing import Optional
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    category: UploadCategory = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Sube un archivo a la categoría especificada.
    Requiere autenticación.

    Args:
        file: El archivo a subir
        category: La categoría del archivo (determina la carpeta)
        description: Descripción opcional del archivo
        current_user: Usuario autenticado (inyectado automáticamente)

    Returns:
        dict: Información sobre el archivo subido
    """
    try:
        url = save_uploaded_file(file, category)
        return {
            "message": "Upload successful",
            "url": url,
            "filename": file.filename,
            "content_type": file.content_type,
            "category": category,
            "description": description,
            "user_id": current_user.id
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

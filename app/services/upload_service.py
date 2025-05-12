import os
import uuid
from fastapi import UploadFile, HTTPException
from typing import Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

# Definir tipos de documentos y sus categorías


class DocumentType(str, Enum):
    # Documentos del conductor
    DRIVER_PROFILE = "profile"           # Foto de perfil del conductor
    DRIVER_SELFIE = "selfie"            # Selfie del conductor
    DRIVER_ID_FRONT = "id_front"        # Frente de cédula
    DRIVER_ID_BACK = "id_back"          # Reverso de cédula
    DRIVER_LICENSE_FRONT = "license_front"  # Frente de licencia
    DRIVER_LICENSE_BACK = "license_back"    # Reverso de licencia
    DRIVER_CRIMINAL_RECORD = "criminal_record"  # Registro criminal

    # Documentos del vehículo
    VEHICLE_PHOTO = "vehicle_photo"     # Foto del vehículo
    VEHICLE_PROPERTY_FRONT = "property_front"  # Frente de tarjeta de propiedad
    VEHICLE_PROPERTY_BACK = "property_back"    # Reverso de tarjeta de propiedad
    VEHICLE_SOAT = "soat"               # SOAT
    VEHICLE_TECHNICAL = "technical"     # Revisión técnico mecánica

    @classmethod
    def _missing_(cls, value):
        """Maneja valores no encontrados en el enum."""
        raise ValueError(
            f"Tipo de documento inválido: {value}. Debe ser uno de: {', '.join(cls.__members__.keys())}")


# Mapeo de tipos de documentos a sus categorías
DOCUMENT_CATEGORIES = {
    # Documentos del conductor
    DocumentType.DRIVER_PROFILE: "driver/profile",
    DocumentType.DRIVER_SELFIE: "driver/selfie",
    DocumentType.DRIVER_ID_FRONT: "driver/id",
    DocumentType.DRIVER_ID_BACK: "driver/id",
    DocumentType.DRIVER_LICENSE_FRONT: "driver/license",
    DocumentType.DRIVER_LICENSE_BACK: "driver/license",
    DocumentType.DRIVER_CRIMINAL_RECORD: "driver/criminal_record",

    # Documentos del vehículo
    DocumentType.VEHICLE_PHOTO: "vehicle/photo",
    DocumentType.VEHICLE_PROPERTY_FRONT: "vehicle/property",
    DocumentType.VEHICLE_PROPERTY_BACK: "vehicle/property",
    DocumentType.VEHICLE_SOAT: "vehicle/soat",
    DocumentType.VEHICLE_TECHNICAL: "vehicle/technical"
}

# Mapeo de campos del modelo a tipos de documentos
MODEL_FIELD_TO_DOCUMENT_TYPE = {
    # DriverInfo fields
    "selfie_url": DocumentType.DRIVER_SELFIE,
    "id_card_front_url": DocumentType.DRIVER_ID_FRONT,
    "id_card_back_url": DocumentType.DRIVER_ID_BACK,

    # DriverDocuments fields
    "property_card_front_url": DocumentType.VEHICLE_PROPERTY_FRONT,
    "property_card_back_url": DocumentType.VEHICLE_PROPERTY_BACK,
    "license_front_url": DocumentType.DRIVER_LICENSE_FRONT,
    "license_back_url": DocumentType.DRIVER_LICENSE_BACK,
    "soat_url": DocumentType.VEHICLE_SOAT,
    "vehicle_technical_inspection_url": DocumentType.VEHICLE_TECHNICAL
}

# Extensiones permitidas por tipo de documento
ALLOWED_EXTENSIONS = {
    DocumentType.DRIVER_PROFILE: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_SELFIE: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_ID_FRONT: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_ID_BACK: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_LICENSE_FRONT: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_LICENSE_BACK: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.DRIVER_CRIMINAL_RECORD: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.VEHICLE_PHOTO: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.VEHICLE_PROPERTY_FRONT: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.VEHICLE_PROPERTY_BACK: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.VEHICLE_SOAT: {".jpg", ".jpeg", ".png", ".pdf"},
    DocumentType.VEHICLE_TECHNICAL: {".jpg", ".jpeg", ".png", ".pdf"}
}

# Tamaños máximos por tipo de documento (en bytes)
MAX_FILE_SIZES = {
    DocumentType.DRIVER_PROFILE: 2 * 1024 * 1024,  # 2MB
    DocumentType.DRIVER_SELFIE: 2 * 1024 * 1024,  # 2MB
    DocumentType.DRIVER_ID_FRONT: 5 * 1024 * 1024,  # 5MB
    DocumentType.DRIVER_ID_BACK: 5 * 1024 * 1024,  # 5MB
    DocumentType.DRIVER_LICENSE_FRONT: 5 * 1024 * 1024,  # 5MB
    DocumentType.DRIVER_LICENSE_BACK: 5 * 1024 * 1024,  # 5MB
    DocumentType.DRIVER_CRIMINAL_RECORD: 10 * 1024 * 1024,  # 10MB
    DocumentType.VEHICLE_PHOTO: 2 * 1024 * 1024,  # 2MB
    DocumentType.VEHICLE_PROPERTY_FRONT: 5 * 1024 * 1024,  # 5MB
    DocumentType.VEHICLE_PROPERTY_BACK: 5 * 1024 * 1024,  # 5MB
    DocumentType.VEHICLE_SOAT: 10 * 1024 * 1024,  # 10MB
    DocumentType.VEHICLE_TECHNICAL: 10 * 1024 * 1024  # 10MB
}


class UploadService:
    def __init__(self):
        self.base_upload_dir = Path("static/uploads")
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    def _validate_file(self, file: UploadFile, document_type: DocumentType) -> None:
        """Valida el archivo según su tipo de documento."""
        # Verificar extensión
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS[document_type]:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido para {document_type}. "
                f"Extensiones permitidas: {', '.join(ALLOWED_EXTENSIONS[document_type])}"
            )

        # Verificar tamaño
        if file.size and file.size > MAX_FILE_SIZES[document_type]:
            max_size_mb = MAX_FILE_SIZES[document_type] / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"El archivo es demasiado grande para {document_type}. "
                f"Tamaño máximo: {max_size_mb}MB"
            )

    def _generate_file_path(self, user_id: int, document_type: DocumentType) -> tuple[Path, str]:
        """Genera la ruta del archivo y su nombre único."""
        # Obtener la categoría del documento
        category = DOCUMENT_CATEGORIES[document_type]

        # Crear la estructura de carpetas: static/uploads/category/user_id/
        file_dir = self.base_upload_dir / category / str(user_id)
        file_dir.mkdir(parents=True, exist_ok=True)

        # Generar nombre único con timestamp y UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Default a .jpg si no hay extensión
        file_ext = os.path.splitext(document_type)[1] or ".jpg"
        unique_name = f"{timestamp}_{uuid.uuid4().hex}{file_ext}"

        return file_dir / unique_name, f"/static/uploads/{category}/{user_id}/{unique_name}"

    async def save_document(
        self,
        file: UploadFile,
        user_id: int,
        document_type: DocumentType,
        description: Optional[str] = None
    ) -> dict:
        """
        Guarda un documento y retorna su información.

        Args:
            file: Archivo a guardar
            user_id: ID del usuario
            document_type: Tipo de documento
            description: Descripción opcional del documento

        Returns:
            dict: Información del documento guardado
        """
        # Validar el archivo
        self._validate_file(file, document_type)

        # Generar ruta y nombre del archivo
        file_path, relative_url = self._generate_file_path(
            user_id, document_type)

        # Guardar el archivo
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al guardar el archivo: {str(e)}"
            )

        # Retornar información del documento
        return {
            "url": relative_url,
            "type": document_type,
            "user_id": user_id,
            "description": description,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "uploaded_at": datetime.now().isoformat()
        }

    def get_document_url(self, relative_url: str) -> str:
        """Obtiene la URL completa del documento."""
        return f"/static/uploads/{relative_url}"

    def delete_document(self, relative_url: str) -> None:
        """Elimina un documento."""
        try:
            file_path = self.base_upload_dir / \
                relative_url.lstrip("/static/uploads/")
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al eliminar el archivo: {str(e)}"
            )


# Instancia global del servicio
upload_service = UploadService()

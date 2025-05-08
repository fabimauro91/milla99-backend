import os
import uuid
from fastapi import UploadFile, HTTPException
from typing import Literal
from datetime import datetime

# Definir carpetas válidas dentro de static/uploads
UploadCategory = Literal[
    "profile_photos",      # Fotos de perfil
    "licenses",           # Licencias de conducción
    "criminal_records",   # Registros criminales
    "vehicles",          # Fotos de vehículos
    "property_cards",    # Tarjetas de propiedad
    "soats",            # SOATs
    "id_cards"          # Cédulas de identidad
]

# Mapeo de categorías a subcarpetas
CATEGORY_SUBFOLDERS = {
    "profile_photos": "drivers",
    "licenses": "drivers",
    "criminal_records": "drivers",
    "vehicles": "drivers",
    "property_cards": "drivers",
    "soats": "drivers",
    "id_cards": "drivers",

}

# Extensiones permitidas
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

FIELD_TO_CATEGORY = {
    "photo_url": "profile_photos",
    "license_selfie_url": "licenses",
    "license_front_url": "licenses",
    "license_back_url": "licenses",
    "criminal_record_url": "criminal_records",
    "vehicle_photo_url": "vehicles",
    "property_card_front_url": "property_cards",
    "property_card_back_url": "property_cards",
    "soat_photo": "soats",
    "id_card_front_url": "id_cards",
    "id_card_back_url": "id_cards"
}


def validate_file(file: UploadFile) -> None:
    """Valida el archivo antes de guardarlo."""
    # Verificar extensión
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Verificar tamaño (máximo 5MB)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="El archivo es demasiado grande. Tamaño máximo: 5MB"
        )


def save_uploaded_file(file: UploadFile, category: str) -> str:
    """
    Guarda un archivo subido en la carpeta correspondiente.

    Args:
        file: El archivo a guardar
        category: La categoría del archivo (determina la carpeta)

    Returns:
        str: La URL relativa del archivo guardado
    """
    validate_file(file)

    # Obtener la subcarpeta para la categoría
    subfolder = CATEGORY_SUBFOLDERS.get(category, "misc")

    # Crear la estructura de carpetas
    base_folder = os.path.join("static", "uploads", subfolder, category)
    os.makedirs(base_folder, exist_ok=True)

    # Generar nombre único con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{timestamp}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(base_folder, unique_name)

    # Guardar el archivo
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el archivo: {str(e)}"
        )

    # Retornar la URL relativa
    return f"/static/uploads/{subfolder}/{category}/{unique_name}"

import os
import uuid
from fastapi import UploadFile
from typing import Literal

# Definir carpetas válidas dentro de static/uploads
UploadCategory = Literal[
    "user_photos",
    "licenses",
    "vehicles",
    "property_cards",
    "soats",
    "id_cards",
    "criminal_records"
]


def save_uploaded_file(file: UploadFile, category: UploadCategory) -> str:
    base_folder = os.path.join("static", "uploads", category)
    os.makedirs(base_folder, exist_ok=True)  # Crea la carpeta si no existe

    # Generar nombre único
    file_ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(base_folder, unique_name)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return f"/static/uploads/{category}/{unique_name}"

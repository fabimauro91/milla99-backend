import os
import uuid
from datetime import datetime
from fastapi import UploadFile
from typing import Optional
from pathlib import Path
from app.core.config import settings


class FileUploader:
    def __init__(self, base_path: str = "static/uploads"):
        self.base_path = base_path
        self._ensure_base_path()

    def _ensure_base_path(self):
        """Asegura que el directorio base exista"""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Genera un nombre de archivo único usando UUID y timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = os.path.splitext(original_filename)[1]
        return f"{timestamp}_{unique_id}{extension}"

    def _get_driver_path(self, driver_id: int) -> str:
        """Obtiene la ruta del directorio para un conductor específico"""
        return os.path.join(self.base_path, "drivers", str(driver_id))

    async def save_driver_document(
        self,
        file: UploadFile,
        driver_id: int,
        document_type: str,
        subfolder: Optional[str] = None
    ) -> str:
        """
        Guarda un documento del conductor manteniendo un historial de versiones.

        Args:
            file: Archivo a subir
            driver_id: ID del conductor
            document_type: Tipo de documento (license, soat, etc.)
            subfolder: Subcarpeta opcional (front, back, etc.)

        Returns:
            str: URL relativa del archivo guardado
        """
        # Crear estructura de directorios
        driver_path = self._get_driver_path(driver_id)
        document_path = os.path.join(driver_path, document_type)
        if subfolder:
            document_path = os.path.join(document_path, subfolder)

        # Asegurar que los directorios existan
        Path(document_path).mkdir(parents=True, exist_ok=True)

        # Generar nombre único para el archivo
        filename = self._generate_unique_filename(file.filename)
        file_path = os.path.join(document_path, filename)

        # Guardar el archivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Retornar la URL relativa
        return os.path.relpath(file_path, self.base_path)

    def get_file_url(self, relative_path: str) -> str:
        """Convierte una ruta relativa en una URL absoluta usando el prefijo de settings"""
        return f"{settings.STATIC_URL_PREFIX}/{relative_path.replace(os.sep, '/')}"


# Instancia global del uploader
uploader = FileUploader()

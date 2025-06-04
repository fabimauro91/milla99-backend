from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Union
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    def __init__(self):
        # La clave de encriptación debe estar en variables de entorno en producción
        self._key = os.getenv('ENCRYPTION_KEY')
        if not self._key:
            # En desarrollo, generamos una clave (NO USAR EN PRODUCCIÓN)
            self._key = Fernet.generate_key()
            logger.warning(
                "Using generated encryption key. In production, set ENCRYPTION_KEY environment variable.")

        # Convertir la clave a bytes si es string
        if isinstance(self._key, str):
            self._key = self._key.encode()

        self._fernet = Fernet(self._key)

    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encripta datos sensibles.

        Args:
            data: String o bytes a encriptar

        Returns:
            String encriptado en base64
        """
        if isinstance(data, str):
            data = data.encode()

        try:
            encrypted_data = self._fernet.encrypt(data)
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            raise

    def decrypt(self, encrypted_data: Union[str, bytes]) -> str:
        """
        Desencripta datos previamente encriptados.

        Args:
            encrypted_data: String o bytes encriptados en base64

        Returns:
            String desencriptado
        """
        if isinstance(encrypted_data, str):
            encrypted_data = base64.b64decode(encrypted_data)

        try:
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise


# Instancia global del servicio de encriptación
encryption_service = EncryptionService()

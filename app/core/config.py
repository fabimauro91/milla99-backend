from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List

class Settings(BaseSettings):
    # Configuración de la aplicación
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    
    # Configuración de la base de datos
    DATABASE_URL: str
    
    # Configuración CORS
    CORS_ORIGINS: List[str]
    CORS_CREDENTIALS: bool
    CORS_METHODS: List[str]
    CORS_HEADERS: List[str]

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    # WhatsApp API Settings
    WHATSAPP_API_URL: str
    WHATSAPP_API_TOKEN: str
    WHATSAPP_PHONE_ID: str
    VERIFICATION_CODE_EXPIRY_MINUTES: int = 10
    MAX_VERIFICATION_ATTEMPTS: int = 3

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

settings = Settings() 
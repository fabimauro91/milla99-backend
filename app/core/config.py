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

    # Teléfono de prueba para usuario de prueba
    TEST_CLIENT_PHONE: str

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

settings = Settings() 
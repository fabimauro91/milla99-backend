from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    # Configuración de la aplicación
    APP_NAME: str = "Milla99 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Configuración de la base de datos
    DATABASE_URL: str = "sqlite:///./milla99.db"
    
    # Configuración CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # Teléfono de prueba para usuario de prueba
    TEST_CLIENT_PHONE: str = "+573148780278"

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

    SECRET_KEY: str = "efdfd804e424be4cd3d4c94f7769da129c45ff2a4a7a1c365e8641715f621000"  # Deberías cambiar esto
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    TWILIO_ACCOUNT_SID: str  # Reemplaza con tu SID
    TWILIO_AUTH_TOKEN :str    # Reemplaza con tu Token
    TWILIO_PHONE_NUMBER :str # Número de Twilio

    CLICK_SEND_USERNAME: str
    CLICK_SEND_PASSWORD: str
    CLICK_SEND_PHONE: str

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    # Configuración de ClickSend
    CLICK_SEND_USERNAME: str
    CLICK_SEND_PASSWORD: str
    CLICK_SEND_PHONE: str

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 
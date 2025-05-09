from fastapi import APIRouter, Depends, status
from ..core.db import SessionDep
from ..services.auth_service import AuthService
from pydantic import BaseModel
from app.models.user import UserRead


router = APIRouter(prefix="/auth", tags=["auth"])

   # Crear un router con prefijo '/whatsapp' y etiqueta para la documentación

class VerificationRequest(BaseModel):   # Modelo para la solicitud de verificación (cuando el usuario envía el código)
    code: str

class VerifResponseCode(BaseModel):  # Endpoint para enviar el código de verificación
     message: str
     access_token: str | None = None
     token_type: str | None = None
     user: UserRead | None = None

class VerificationResponse(BaseModel):  # Endpoint para enviar el código de verificación
     message: str

class SMSMessage(BaseModel):
    phone_number: str
    message: str

@router.post(                                       # Decorador que indica que es una ruta POST
    "/verify/{country_code}/{phone_number}/send",                       # Ruta con parámetro user_id
    response_model=VerificationResponse,            # Modelo de respuesta
    status_code=status.HTTP_201_CREATED             # Código de estado 201 (Created)
)

async def send_verification(country_code: str, phone_number: str, session: SessionDep): # ID del usuario que se va a verificar, Sesión de base de datos (inyectada automáticamente)
    """Send verification code via WhatsApp"""
    service = AuthService(session)                                          # Crear una instancia del servicio
    verification, codigo = await service.create_verification(country_code,phone_number)                   # Llamar al método para crear y enviar la verificación
    return VerificationResponse(message=f"Verification code sent successfully {codigo}")  # Retornar mensaje de éxito

@router.post(                                       # Endpoint para verificar el código recibido
    "/verify/{country_code}/{phone_number}/code",                       # Ruta para verificar el código
    response_model=VerifResponseCode             # Modelo de respuesta
)

async def verify_code(
    country_code: str,
    phone_number: str,                                   # ID del usuario
    verification: VerificationRequest,              # Datos de la solicitud (el código)
    session: SessionDep                             # Sesión de base de datos
):
    """Verify the code sent via WhatsApp"""
    service = AuthService(session)                                  # Crear instancia del servicio
    result, access_token, user = service.verify_code(country_code, phone_number, verification.code)            # Verificar el código
    print(access_token)
    return VerifResponseCode(
        message="Code verified successfully",
        access_token=access_token,
        token_type="bearer",
        user=UserRead.model_validate(user, from_attributes=True)
    )
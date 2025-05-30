from fastapi import APIRouter, Depends, status, HTTPException
from ..core.db import SessionDep
from ..services.auth_service import AuthService
from pydantic import BaseModel
from app.models.user import UserRead
import logging


router = APIRouter(prefix="/auth", tags=["auth"])

# Crear un router con prefijo '/whatsapp' y etiqueta para la documentación


# Modelo para la solicitud de verificación (cuando el usuario envía el código)
class VerificationRequest(BaseModel):
    code: str


# Endpoint para enviar el código de verificación
class VerifResponseCode(BaseModel):
    message: str
    access_token: str | None = None
    token_type: str | None = None
    user: UserRead | None = None


# Endpoint para enviar el código de verificación
class VerificationResponse(BaseModel):
    message: str


class SMSMessage(BaseModel):
    phone_number: str
    message: str


@router.post(
    "/verify/{country_code}/{phone_number}/send",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
    description="""
Envía un código de verificación vía WhatsApp al número de teléfono proporcionado.

**Parámetros:**
- `country_code`: Código de país del usuario.
- `phone_number`: Número de teléfono del usuario.

**Respuesta:**
Devuelve un mensaje indicando que el código de verificación fue enviado exitosamente.
"""
)
# ID del usuario que se va a verificar, Sesión de base de datos (inyectada automáticamente)
async def send_verification(country_code: str, phone_number: str, session: SessionDep):
    """Send verification code via WhatsApp"""
    service = AuthService(
        session)                                          # Crear una instancia del servicio
    # Llamar al método para crear y enviar la verificación
    verification, codigo = await service.create_verification(country_code, phone_number)
    # Retornar mensaje de éxito
    return VerificationResponse(message=f"Verification code sent successfully {codigo}")


@router.post(
    "/verify/{country_code}/{phone_number}/code",
    response_model=VerifResponseCode,
    description="""
Verifica el código recibido vía WhatsApp para el número de teléfono proporcionado.

**Parámetros:**
- `country_code`: Código de país del usuario.
- `phone_number`: Número de teléfono del usuario.
- `code`: Código de verificación recibido por el usuario.

**Respuesta:**
Devuelve un mensaje indicando si la verificación fue exitosa, junto con el token de acceso y la información del usuario si aplica.
"""
)
async def verify_code(
    country_code: str,
    phone_number: str,                                   # ID del usuario
    # Datos de la solicitud (el código)
    verification: VerificationRequest,
    session: SessionDep                             # Sesión de base de datos
):
    """Verify the code sent via WhatsApp"""
    service = AuthService(session)  # crear instancia del servicio
    try:
        result, access_token, user = service.verify_code(
            country_code, phone_number, verification.code)  # verificar el código
        return VerifResponseCode(
            message="Code verified successfully",
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user, from_attributes=True)
        )
    except HTTPException as e:
        # Errores esperados (usuario no encontrado, código inválido, etc.)
        raise e
    except Exception as e:
        # Loguear el error inesperado
        logging.exception("Unexpected error verifying code")
        raise HTTPException(status_code=500, detail="Internal server error")

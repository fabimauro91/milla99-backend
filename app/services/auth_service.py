import random
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlmodel import Session, select
from ..models.w_verification import Verification, VerificationCreate
from ..models.user import User
from ..core.config import settings
from jose import jwt
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def generate_verification_code(self) -> str:
        return ''.join(random.choices('0123456789', k=6))

    async def send_whatsapp_message(self, to_phone: str, message: str) -> bool:
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages",
                    headers=headers,
                    json=payload
                )
                print("Payload enviado:", payload)
                print("Respuesta de WhatsApp:",
                      response.status_code, response.text)
                response.raise_for_status()
                return True
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send WhatsApp message: {str(e)}"
            )

    async def create_verification(self, country_code: str, phone_number: str) -> tuple[Verification, str]:
        # Verificar usuario existente
        user = self.session.exec(
            select(User).where(
                User.country_code == country_code,
                User.phone_number == phone_number
            )
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Generar código y fecha de expiración
        verification_code = self.generate_verification_code()
        expires_at = datetime.utcnow(
        ) + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

        # Buscar si ya existe una verificación para este usuario
        existing_verification = self.session.exec(
            select(Verification).where(Verification.user_id == user.id)
        ).first()

        if existing_verification:
            # Actualizar el registro existente
            existing_verification.is_verified = False
            existing_verification.verification_code = verification_code
            existing_verification.expires_at = expires_at
            existing_verification.attempts = 0
            self.session.add(existing_verification)
            self.session.commit()
            self.session.refresh(existing_verification)
            verif = existing_verification
        else:
            # Crear la nueva verificación
            verif = Verification(
                user_id=user.id,
                verification_code=verification_code,
                expires_at=expires_at,
                is_verified=False
            )
            self.session.add(verif)
            self.session.commit()
            self.session.refresh(verif)

        try:
            # Enviar mensaje WhatsApp
            full_phone = f"{country_code}{phone_number}"
            message = f"Your verification code is: {verification_code}. This code will expire in {settings.VERIFICATION_CODE_EXPIRY_MINUTES} minutes."

            await self.send_whatsapp_message(full_phone, message)
            # await self.generate_mns_verification(full_phone, message)

            return verif, verification_code
        except Exception as e:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in verification process: {str(e)}"
            )

    def verify_code(self, country_code: str, phone_number: str, code: str) -> tuple[bool, str, User]:
        # Buscar el usuario primero
        user = self.session.exec(
            select(User).where(
                User.country_code == country_code,
                User.phone_number == phone_number
            )
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        verification = self.session.exec(
            select(Verification)
            .where(
                Verification.user_id == user.id,
                Verification.expires_at > datetime.utcnow(),
                Verification.is_verified == False
            )
        ).first()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active verification found"
            )

        if verification.attempts >= settings.MAX_VERIFICATION_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded"
            )

        verification.attempts += 1

        if verification.verification_code != code:
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        verification.is_verified = True
        self.session.commit()

        # Actualizar estado de verificación del usuario
        if not user.is_verified_phone:
            user.is_verified_phone = True
        if not user.is_active:
            user.is_active = True

        self.session.commit()

        # Generar token JWT
        access_token = self.create_access_token(user.id)

        return True, access_token, user

    def create_access_token(self, user_id: int):
        to_encode = {"sub": str(user_id)}
        # Convertir minutos a timedelta
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def generate_mns_verification(self, to_phone: str, message: str) -> dict:
        try:
            # Asegurarse de que el número tenga el formato correcto
            if not to_phone.startswith('+'):
                to_phone = f'+{to_phone}'

            configuration = clicksend_client.Configuration()
            configuration.username = settings.CLICK_SEND_USERNAME
            configuration.password = settings.CLICK_SEND_PASSWORD

            # Crear instancia de la API     para instalar pip install clicksend-client
            api_instance = clicksend_client.SMSApi(
                clicksend_client.ApiClient(configuration))

            message_list = {
                "messages": [
                    {
                        "source": "milla99",
                        "body": message,
                        "to": to_phone,
                        "from": settings.CLICK_SEND_PHONE
                    }
                ]
            }

            # Enviar mensaje
            api_response = api_instance.sms_send_post(message_list)
            print(str(api_response))

        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS: {str(e)}"
            )

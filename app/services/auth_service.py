import random
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlmodel import Session, select
from ..models.w_verification import Verification, VerificationCreate
from ..models.user import User
from ..core.config import settings
from jose import jwt
from twilio.rest import Client


class authService:
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
                print("Respuesta de WhatsApp:", response.status_code, response.text)
                response.raise_for_status()
                return True
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send WhatsApp message: {str(e)}"
            )

    async def create_verification(self, phone_number: str) -> tuple[Verification, str]:
        try:
            # Verificar usuario existente por número de teléfono
            user_query = select(User).where(
                User.phone_number == phone_number.lstrip('+')  # Removemos el '+' si existe
            )
            user = self.session.exec(user_query).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User not found with phone number: {phone_number}"
                )

            # Verificar si existe una verificación activa
            active_verification = self.session.exec(
                select(Verification)
                .where(
                    Verification.user_id == user.id,
                    Verification.expires_at > datetime.utcnow(),
                    Verification.is_verified == False
                )
            ).first()

            if active_verification:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Active verification already exists"
                )

            # Generar nueva verificación
            verification_code = self.generate_verification_code()
            expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

            verification_data = VerificationCreate(
                user_id=user.id,  # Usamos el ID del usuario encontrado
                verification_code=verification_code,
                expires_at=expires_at
            )

            verification = Verification.model_validate(verification_data.model_dump())
            self.session.add(verification)
            self.session.commit()
            self.session.refresh(verification)

            try:
                # Preparar el número de teléfono completo
                full_phone = f"{user.country_code}{user.phone_number}"
                message = f"Your verification code is: {verification_code}. This code will expire in {settings.VERIFICATION_CODE_EXPIRY_MINUTES} minutes."

                # Intentar enviar por ambos canales
                whatsapp_result = await self.send_whatsapp_message(full_phone, message)
                #ms_result = await self.generate_mns_verification(full_phone, message)

                return verification, verification_code

            except Exception as send_error:
                print(f"Error sending messages: {str(send_error)}")
                self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error sending verification messages: {str(send_error)}"
                )

        except HTTPException as http_error:
            # Re-lanzar excepciones HTTP
            raise http_error
        except Exception as e:
            print(f"Unexpected error in create_verification: {str(e)}")
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in verification process: {str(e)}"
        )
    
    def verify_code(self, phone_number: str, code: str) -> tuple[bool, str]:

        # Verificar usuario existente por número de teléfono
        user_query = select(User).where(
            User.phone_number == phone_number.lstrip('+')  # Removemos el '+' si existe
        )
        user = self.session.exec(user_query).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found with phone number: {phone_number}"
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
        user = self.session.get(User, user.id)
        user.is_verified = True
        self.session.commit()

        # Generar token JWT
        access_token = self.create_access_token(user.id)

        return True, access_token
    
    def create_access_token(self, user_id: int):
        to_encode = {"sub": str(user_id)}
        # Convertir minutos a timedelta
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def generate_mns_verification(self, to_phone: str, message: str) -> dict:
        try:
            # Asegurarse de que el número tenga el formato correcto
            if not to_phone.startswith('+'):
                to_phone = f'+{to_phone}'

            # Crear el cliente de Twilio
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            # Enviar el mensaje
            message_response = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone
            )

            # Logging para debugging
            print(f"Message sent successfully to {to_phone}. SID: {message_response.sid}")

            return {
                "status": "success",
                "message_sid": message_response.sid,
                "detail": "Message sent successfully",
                "to": to_phone
            }

        except Exception as e:
            print(f"Error sending SMS: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send SMS: {str(e)}"
            )
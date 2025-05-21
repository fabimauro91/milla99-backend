# app/services/earnings_service.py
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client_request import ClientRequest, StatusEnum
from app.models.referral_chain import Referral
from app.models.profit_sharing_record import Earning
from app.models.user import User
import jwt
from datetime import datetime, timedelta
import base64
import json
from app.core.config import settings

# Id especial (o None) para la empresa
COMPANY_ID: int | None = None

def _get_referral_chain(session, user_id: int, levels: int = 3) -> list[int]:
    chain = []
    current_id = user_id

    for _ in range(levels):
        stmt = select(Referral).where(Referral.user_id == current_id)
        result = session.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel or not rel.referred_by_id:
            break
        chain.append(rel.referred_by_id)
        current_id = rel.referred_by_id

    return chain

def distribute_earnings(session, request: ClientRequest) -> None:
    if request.status != StatusEnum.FINISHED:
        return

    fare = Decimal(str(request.fare_assigned or 0))
    if fare <= 0:
        return

    total_box = fare * Decimal("0.10")
    driver_saving = fare * Decimal("0.01")
    remaining_box = total_box - driver_saving
    company_base_share = fare * Decimal("0.04")
    referrals_total = fare * Decimal("0.05")
    each_ref_share = (referrals_total / 3).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)

    chain_ids = _get_referral_chain(session, request.id_client, levels=3)

    earnings = []

    earnings.append(Earning(
        client_request_id=request.id,
        user_id=request.id_driver_assigned,
        amount=float(driver_saving),
        concept="driver_saving"
    ))

    company_share = company_base_share

    for idx in range(3):
        if idx < len(chain_ids):
            earnings.append(Earning(
                client_request_id=request.id,
                user_id=chain_ids[idx],
                amount=float(each_ref_share),
                concept=f"referral_{idx+1}"
            ))
        else:
            company_share += each_ref_share

    earnings.append(Earning(
        client_request_id=request.id,
        user_id=COMPANY_ID,
        amount=float(company_share),
        concept="company"
    ))

    session.add_all(earnings)
    session.commit()


def generate_referral_link(session, user_id: int) -> str:
    """
    Genera un enlace de referido para un usuario específico.
    El enlace contiene información codificada sobre el usuario que refiere.
    """
    # Verificar que el usuario existe
    user = session.exec(
        select(User).where(User.id == user_id)
    ).first()

    if not user:
        raise ValueError(f"Usuario con ID {user_id} no encontrado")

    # Crear payload con información del referente
    payload = {
        "referrer_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=30)  # El link expira en 30 días
    }

    # Generar token firmado
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    # Crear el enlace completo
    base_url = settings.APP_URL if hasattr(settings, 'APP_URL') else "https://milla99.com"
    referral_link = f"{base_url}/register?ref={token}"

    return referral_link

def validate_referral_token(session, token: str) -> Optional[int]:
        """
        Valida un token de referido y devuelve el ID del usuario referente.
        """
        try:
            # Decodificar el token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            # Verificar que el token no ha expirado
            if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                return None

            # Devolver el ID del referente
            return payload["referrer_id"]
        except:
            return None
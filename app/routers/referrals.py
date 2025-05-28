# app/routes/client_request.py

from fastapi import APIRouter, HTTPException, status
from ..core.db import SessionDep
from app.services.earnings_service import get_referral_earnings_structured
from uuid import UUID

router = APIRouter(prefix="/referrals", tags=["referrals"])

@router.get("/{user_id}/earnings-structured")
def get_referral_earnings_structured_api(
    user_id: UUID,
    session: SessionDep
):
    """
    Devuelve el resumen estructurado de ganancias de referidos para un usuario. 
    """
    try:
        data = get_referral_earnings_structured(session, user_id)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener ganancias de referidos: {str(e)}"
        )
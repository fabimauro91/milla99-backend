# app/routes/client_request.py

from fastapi import APIRouter, HTTPException, status, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..core.db import SessionDep
from app.services.earnings_service import get_referral_earnings_structured

router = APIRouter(prefix="/referrals", tags=["referrals"])

bearer_scheme = HTTPBearer()


@router.get("/me/earnings-structured")
def get_referral_earnings_structured_api(
    request: Request,
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Devuelve el resumen estructurado de ganancias de referidos para el usuario autenticado (toma el user_id desde el token).
    """
    try:
        # Obtener el user_id desde el token
        user_id = request.state.user_id
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

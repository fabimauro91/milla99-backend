# app/routes/client_request.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select
from starlette.concurrency import run_in_threadpool
from ..core.db import SessionDep,get_session
from app.models.client_request import ClientRequest, StatusEnum
from app.models.user import User
from app.models.referral_chain import Referral, ReferralLinkResponse
from app.services.earnings_service import distribute_earnings, generate_referral_link, validate_referral_token
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/referrals", tags=["referrals"])

@router.post("/{request_id}/share-profits")
def finish_request(
    request_id: int,
    session: SessionDep
):
    stmt = select(ClientRequest).where(ClientRequest.id == request_id)
    result = session.execute(stmt)
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    if request.status != StatusEnum.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La carrera debe estar en estado CANCELLED para poder finalizarla"
        )

    if request.status == StatusEnum.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The request is already finished"
        )

    request.status = StatusEnum.FINISHED
    session.commit()
    session.refresh(request)

    distribute_earnings(session, request)  # SIN await

    return {"message": "Carrera finalizada y ganancias distribuidas"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_referral(
    session: SessionDep,
    user_id: int = Query(..., description="ID del usuario referido"),
    referred_by_id: int = Query(..., description="ID del usuario que refiere"),
    
):
    """
    Crea una relación de referido entre dos usuarios.
    """
    # Ejecutar en un pool de hilos para evitar problemas con operaciones síncronas
    return await run_in_threadpool(
        _create_referral_sync, user_id, referred_by_id, session
    )

def _create_referral_sync(user_id: int, referred_by_id: int, session):
    """Versión síncrona para crear un referido"""
    try:
        # Verificar que ambos usuarios existen - operaciones síncronas
        user_stmt = select(User).where(User.id == user_id)
        user = session.execute(user_stmt).scalar_one_or_none()

        referrer_stmt = select(User).where(User.id == referred_by_id)
        referrer = session.execute(referrer_stmt).scalar_one_or_none()

        if not user or not referrer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno o ambos usuarios no existen"
            )

        # Verificar que no exista ya un referido para este usuario
        stmt = select(Referral).where(Referral.user_id == user_id)
        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user_id} ya tiene un referente registrado"
            )

        # Crear el referido
        referral = Referral(user_id=user_id, referred_by_id=referred_by_id)
        session.add(referral)
        session.commit()

        return {
            "id": referral.id,
            "user_id": referral.user_id,
            "referred_by_id": referral.referred_by_id,
            "message": "Referido registrado correctamente"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el servidor: {str(e)}"
        )
    

# Añadir nuevas rutas para la generación y envío de enlaces de referido
@router.get("/generate-link", response_model=ReferralLinkResponse)
def referral_link(
    session: SessionDep,
    user_id: int = Query(..., description="ID del usuario que genera el enlace de referido"),
):
    """
    Genera un enlace de referido para un usuario específico.
    """
    try:
        referral_link = generate_referral_link(session,user_id)

        return ReferralLinkResponse(
            referral_link=referral_link,
            message="Enlace de referido generado correctamente"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar enlace de referido: {str(e)}"
        )
    

@router.get("/validate-token")
def validate_token(
    session: SessionDep,
    token: str = Query(..., description="Token de referido a validar"),
):
    """
    Valida un token de referido y devuelve información sobre el referente.
    """
    referrer_id = validate_referral_token(session,token)

    if not referrer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de referido inválido o expirado"
        )

    # Obtener información del referente
    referrer = session.exec(
        select(User).where(User.id == referrer_id)
    ).first()

    if not referrer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario referente no encontrado"
        )

    return {
        "referrer_id": referrer_id,
        "referrer_name": referrer.full_name,
        "valid": True
    }
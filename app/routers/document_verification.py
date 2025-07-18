from fastapi import APIRouter, Depends, status, Request, HTTPException, UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Dict, Any

from app.core.dependencies.auth import get_current_user
from app.models.user import User
from app.core.db import SessionDep
from app.services.document_verification_service import DocumentVerificationService
from app.models.driver_info import DriverInfo
from sqlmodel import select
from PIL import Image
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/document-verification",
                   tags=["DRIVER"],
                   dependencies=[Depends(get_current_user)])


def get_document_verification_service() -> DocumentVerificationService:
    """Dependency para obtener el servicio de verificación de identidad"""
    return DocumentVerificationService()


@router.post("/verify-identity", response_model=Dict[str, Any])
async def verify_identity_endpoint(
    document_image: UploadFile = File(...,
                                      description="Imagen del documento de identidad"),
    selfie_image: UploadFile = File(..., description="Selfie del usuario"),
    document_type: str = None,
    current_user: User = Depends(get_current_user),
    service: DocumentVerificationService = Depends(
        get_document_verification_service)
):
    """
    Verificación automática de identidad: documento, selfie y comparación facial

    **Parámetros:**
    - document_image: Imagen del documento de identidad (JPG, PNG)
    - selfie_image: Selfie del usuario (JPG, PNG)
    - document_type: Tipo de documento esperado (opcional)

    **Respuesta:**
    Devuelve el resultado completo de la verificación incluyendo:
    - Puntuación final
    - Decisión (APPROVED, MANUAL_REVIEW, REJECTED)
    - Puntuaciones detalladas por componente
    - Recomendaciones
    - Próximos pasos
    """
    try:
        # Validar tipos de archivo
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        doc_ext = '.' + \
            document_image.filename.split(
                '.')[-1].lower() if '.' in document_image.filename else ''
        selfie_ext = '.' + \
            selfie_image.filename.split(
                '.')[-1].lower() if '.' in selfie_image.filename else ''

        if doc_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de documento no soportado. Use: {', '.join(allowed_extensions)}"
            )

        if selfie_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de selfie no soportado. Use: {', '.join(allowed_extensions)}"
            )

        # Leer contenido de los archivos
        document_data = await document_image.read()
        selfie_data = await selfie_image.read()

        # Validar tamaño de archivos (máximo 10MB cada uno)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(document_data) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo del documento es demasiado grande. Máximo 10MB"
            )

        if len(selfie_data) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo de la selfie es demasiado grande. Máximo 10MB"
            )

        # Comprimir archivos si es necesario antes de enviar a AWS
        document_data = service._compress_if_needed(document_data)
        selfie_data = service._compress_if_needed(selfie_data)

        # Ejecutar verificación completa
        result = service.verify_identity(
            document_data, selfie_data, document_type)

        # Agregar información del usuario al resultado
        result['user_id'] = str(current_user.id)
        result['user_phone'] = current_user.phone_number

        # Log de la verificación
        logger.info(
            f"Verificación automática completada - User: {current_user.id} - Score: {result.get('final_score', 0.0):.3f} - Decision: {result.get('decision', 'UNKNOWN')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error en verificación automática para usuario {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/verification-status", response_model=Dict[str, Any])
async def get_verification_status(
    current_user: User = Depends(get_current_user),
    service: DocumentVerificationService = Depends(
        get_document_verification_service)
):
    """
    Obtiene el estado de verificación del usuario actual
    """
    try:
        # Por ahora retornamos información básica
        # En el futuro esto podría consultar la base de datos
        return {
            "user_id": str(current_user.id),
            "phone_number": current_user.phone_number,
            "verification_available": True,
            "message": "Servicio de verificación automática disponible"
        }
    except Exception as e:
        logger.error(
            f"Error obteniendo estado de verificación para usuario {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/driver-status", response_model=Dict[str, Any])
async def get_driver_verification_status(
    session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el estado de verificación de documentos del driver actual.

    **Respuesta:**
    Devuelve información detallada sobre el estado de verificación de documentos:
    - Estado de verificación (PENDING, APPROVED, REJECTED, MANUAL_REVIEW)
    - Puntuación de verificación
    - Fecha de la última verificación
    - Número de intentos realizados
    - Detalles de la verificación
    """
    try:
        # Buscar DriverInfo del usuario actual
        driver_info = session.exec(
            select(DriverInfo).where(DriverInfo.user_id == current_user.id)
        ).first()

        if not driver_info:
            raise HTTPException(
                status_code=404,
                detail="No se encontró información de conductor para este usuario"
            )

        # Preparar respuesta con información de verificación
        response = {
            "user_id": str(current_user.id),
            "driver_info_id": str(driver_info.id),
            "verification_status": driver_info.document_verification_status,
            "verification_score": driver_info.document_verification_score,
            "verification_date": driver_info.document_verification_date.isoformat() if driver_info.document_verification_date else None,
            "verification_attempts": driver_info.verification_attempts,
            "last_attempt": driver_info.last_verification_attempt.isoformat() if driver_info.last_verification_attempt else None,
            "verification_id": driver_info.document_verification_id,
            "can_operate": driver_info.document_verification_status == "APPROVED",
            "requires_manual_review": driver_info.document_verification_status == "MANUAL_REVIEW",
            "needs_correction": driver_info.document_verification_status == "REJECTED"
        }

        # Agregar detalles de verificación si existen
        if driver_info.document_verification_details:
            response["verification_details"] = driver_info.document_verification_details
            # Agregar recomendaciones si existen
            if "recommendations" in driver_info.document_verification_details:
                response["recommendations"] = driver_info.document_verification_details["recommendations"]

        logger.info(
            f"Estado de verificación consultado - User: {current_user.id} - Status: {driver_info.document_verification_status}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error obteniendo estado de verificación para usuario {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/request-reverification", response_model=Dict[str, Any])
async def request_reverification(
    session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """
    Solicita una nueva verificación de documentos para el driver actual.

    **Respuesta:**
    Devuelve confirmación de la solicitud de re-verificación.
    """
    try:
        # Buscar DriverInfo del usuario actual
        driver_info = session.exec(
            select(DriverInfo).where(DriverInfo.user_id == current_user.id)
        ).first()

        if not driver_info:
            raise HTTPException(
                status_code=404,
                detail="No se encontró información de conductor para este usuario"
            )

        # Verificar que el estado actual permita re-verificación
        if driver_info.document_verification_status == "APPROVED":
            raise HTTPException(
                status_code=400,
                detail="No se puede solicitar re-verificación cuando ya está aprobado"
            )

        # Actualizar estado para indicar nueva verificación pendiente
        driver_info.document_verification_status = "PENDING"
        driver_info.verification_attempts += 1
        driver_info.last_verification_attempt = datetime.now()

        session.add(driver_info)
        session.commit()
        session.refresh(driver_info)

        logger.info(
            f"Re-verificación solicitada - User: {current_user.id} - Intentos: {driver_info.verification_attempts}"
        )

        return {
            "message": "Solicitud de re-verificación registrada exitosamente",
            "user_id": str(current_user.id),
            "verification_attempts": driver_info.verification_attempts,
            "last_attempt": driver_info.last_verification_attempt.isoformat() if driver_info.last_verification_attempt else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error solicitando re-verificación para usuario {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

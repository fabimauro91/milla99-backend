from fastapi import APIRouter, Depends, status, Request, HTTPException, Security, UploadFile, File, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Dict, Any
from datetime import datetime

from app.core.dependencies.admin_auth import get_current_admin
from app.models.user import UserRead
from app.models.driver_documents import DocumentsUpdate, DriverDocuments
from app.core.db import SessionDep
from app.services.verify_docs_service import (
    VerifyDocsService,
    UserWithDocs,
    UserWithExpiringDocsResponse
)
from app.models.driver_documents import DocumentsUpdate, DriverDocumentsCreateRequest
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.services.document_verification_service import DocumentVerificationService
from app.services.notification_service import NotificationService
from app.core.dependencies.admin_auth import get_current_admin_user


bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/verify-docs",
                   tags=["ADMIN"],
                   dependencies=[Depends(get_current_admin)])


def get_verify_docs_service(session: SessionDep) -> VerifyDocsService:
    """Dependency para obtener el servicio de verificación de documentos"""
    return VerifyDocsService(session)


def get_document_verification_service() -> DocumentVerificationService:
    """Dependency para obtener el servicio de verificación de identidad"""
    return DocumentVerificationService()


@router.post("/verify-identity", response_model=Dict[str, Any])
async def verify_identity_endpoint(
    document_image: UploadFile = File(...,
                                      description="Imagen del documento de identidad"),
    selfie_image: UploadFile = File(..., description="Selfie del usuario"),
    document_type: str = None,
    service: DocumentVerificationService = Depends(
        get_document_verification_service)
):
    """
    Verificación completa de identidad: documento, selfie y comparación facial

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

        # Ejecutar verificación completa
        result = service.verify_identity(
            document_data, selfie_data, document_type)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/pending", response_model=List[UserWithDocs])
def get_users_with_pending_docs(
    request: Request,
    session: SessionDep,
):
    """
    Obtiene usuarios con documentos pendientes y sus documentos asociados.

    **Respuesta:**
    Devuelve una lista de usuarios con sus documentos pendientes de aprobación.
    """
    service = VerifyDocsService(session)
    return service.get_users_with_pending_docs()


# @router.get("/approved", response_model=List[UserRead])


def get_users_with_all_approved_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con todos rol de estado aprobados"""
    service = VerifyDocsService(session)
    return service.get_users_with_all_approved_docs()


@router.get("/verification-status", response_model=Dict[str, Any])
def get_verification_status(
    service: VerifyDocsService = Depends(get_verify_docs_service)
):
    """
    Obtiene estadísticas sobre el estado de verificación de los conductores.
    """
    return service.get_verification_status()


# @router.get("/rejected", response_model=List[UserWithDocs])
def get_users_with_rejected_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con documentos rechazados y sus documentos asociados"""
    service = VerifyDocsService(session)
    return service.get_users_with_rejected_docs()


# @router.get("/expired", response_model=List[UserWithDocs])

def get_users_with_expired_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con documentos expirados y sus documentos asociados"""
    service = VerifyDocsService(session)
    return service.get_users_with_expired_docs()


# @router.post("/check-expired", status_code=status.HTTP_200_OK)

def update_expired_documents(
    request: Request,
    session: SessionDep
):
    """Actualiza los documentos con estado aprobados si sus fechas estan vencidas
       Si estan vencidas, el estado cambia a espirado """
    service = VerifyDocsService(session)
    updated_count = service.update_expired_documents()
    return {"message": f"Updated {updated_count} expired documents"}


# @router.get("/check-expiring-soon", response_model=List[UserWithExpiringDocsResponse])

def check_soon_to_expire_documents(
    request: Request,
    session: SessionDep
):
    """Verifica si los usuarios tienen documentos próximos a expirar
        Si tienen un documento que expira en menos de ocho dias, retorna a usuario con el cocumento"""
    service = VerifyDocsService(session)
    return service.check_soon_to_expire_documents()


@router.put("/update-documents", status_code=status.HTTP_200_OK)
def update_documents(
    updates: List[DocumentsUpdate],
    request: Request,
    session: SessionDep
):
    """
    Actualiza múltiples documentos.
    Se puede enciar uno o mas de documentos, cada uno con el id del documento y los datos a actualizar.
    Se debe enviar al menos un documento y al menos un dato a modificar

            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "pending",                                
            "expiration_date": "2025-05-30T16:53:32.029Z",      opcional
            "document_front_url": "string",                     opcional
            "document_back_url": "string"                       opcional

    **Respuesta:**
    Devuelve un mensaje indicando cuántos documentos fueron actualizados correctamente.
    """
    service = VerifyDocsService(session)
    try:
        updated_docs = service.update_documents(updates)
        return {"message": f"Updated {len(updated_docs)} documents"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/debug-driver-status/{user_id}", response_model=Dict[str, Any])
def debug_driver_status(
    user_id: str,
    session: SessionDep
):
    """
    DEBUG: Verifica el estado completo de verificación de un conductor específico.
    """
    from uuid import UUID
    from sqlmodel import select
    from app.models.driver_info import DriverInfo
    from app.models.driver_documents import DriverDocuments, DriverStatus
    from app.models.user_has_roles import UserHasRole
    from sqlalchemy import func

    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # 1. Verificar UserHasRole
    user_role = session.exec(
        select(UserHasRole).where(
            UserHasRole.id_user == user_uuid,
            UserHasRole.id_rol == "DRIVER"
        )
    ).first()

    if not user_role:
        raise HTTPException(status_code=404, detail="Driver role not found")

    # 2. Obtener DriverInfo
    driver_info = session.exec(
        select(DriverInfo).where(DriverInfo.user_id == user_uuid)
    ).first()

    if not driver_info:
        raise HTTPException(status_code=404, detail="DriverInfo not found")

    # 3. Obtener documentos y su estado
    documents = session.exec(
        select(DriverDocuments).where(
            DriverDocuments.driver_info_id == driver_info.id
        )
    ).all()

    # 4. Contar documentos aprobados por tipo
    REQUIRED_DOC_TYPE_IDS = [1, 2, 3, 4]
    approved_required_doc_types_count = session.exec(
        select(func.count(func.distinct(DriverDocuments.document_type_id)))
        .where(
            DriverDocuments.driver_info_id == driver_info.id,
            DriverDocuments.status == DriverStatus.APPROVED,
            DriverDocuments.document_type_id.in_(REQUIRED_DOC_TYPE_IDS)
        )
    ).first() or 0

    # 5. Documentos por tipo y estado
    docs_by_type = {}
    for doc in documents:
        doc_type = doc.document_type_id
        if doc_type not in docs_by_type:
            docs_by_type[doc_type] = []
        docs_by_type[doc_type].append({
            "id": str(doc.id),
            "status": doc.status,
            "expiration_date": doc.expiration_date.isoformat() if doc.expiration_date else None
        })

    return {
        "user_id": str(user_uuid),
        "user_role": {
            "is_verified": user_role.is_verified,
            "status": user_role.status,
            "verified_at": user_role.verified_at.isoformat() if user_role.verified_at else None
        },
        "driver_info_id": str(driver_info.id),
        "documents_analysis": {
            "total_documents": len(documents),
            "required_doc_types_approved": approved_required_doc_types_count,
            "should_be_approved": approved_required_doc_types_count == 4,
            "documents_by_type": docs_by_type
        },
        "required_doc_types": {
            "1": "Tarjeta de Propiedad",
            "2": "Licencia",
            "3": "SOAT",
            "4": "Tecnomecánica"
        }
    }


@router.post("/force-approve-driver/{user_id}")
def force_approve_driver(
    user_id: str,
    session: SessionDep
):
    """
    DEBUG: Fuerza la aprobación de un conductor (para testing)
    """
    from uuid import UUID
    from sqlmodel import select
    from app.models.user_has_roles import UserHasRole, RoleStatus

    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Buscar el UserHasRole del conductor
    user_role = session.exec(
        select(UserHasRole).where(
            UserHasRole.id_user == user_uuid,
            UserHasRole.id_rol == "DRIVER"
        )
    ).first()

    if not user_role:
        raise HTTPException(status_code=404, detail="Driver role not found")

    # Forzar aprobación
    user_role.is_verified = True
    user_role.status = RoleStatus.APPROVED
    session.add(user_role)
    session.commit()
    session.refresh(user_role)

    return {
        "message": "Driver forcefully approved",
        "user_id": str(user_uuid),
        "new_status": {
            "is_verified": user_role.is_verified,
            "status": user_role.status
        }
    }


@router.post("/manual-approve-driver/{user_id}")
def manual_approve_driver(
    user_id: str,
    session: SessionDep,
    current_admin=Depends(get_current_admin_user)
):
    """
    Aprobar manualmente un conductor después de revisión administrativa.
    Envía notificación de aprobación al conductor.
    """
    from uuid import UUID
    from sqlmodel import select
    from app.models.user_has_roles import UserHasRole, RoleStatus
    from app.models.driver_info import DriverInfo
    from app.services.notification_service import NotificationService

    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Buscar el UserHasRole del conductor
    user_role = session.exec(
        select(UserHasRole).where(
            UserHasRole.id_user == user_uuid,
            UserHasRole.id_rol == "DRIVER"
        )
    ).first()

    if not user_role:
        raise HTTPException(status_code=404, detail="Driver role not found")

    # Buscar DriverInfo
    driver_info = session.exec(
        select(DriverInfo).where(DriverInfo.user_id == user_uuid)
    ).first()

    if not driver_info:
        raise HTTPException(status_code=404, detail="DriverInfo not found")

    # Aprobar conductor
    user_role.is_verified = True
    user_role.status = RoleStatus.APPROVED
    user_role.verified_at = datetime.now()

    # Actualizar estado de verificación en DriverInfo
    driver_info.document_verification_status = "APPROVED"
    driver_info.document_verification_date = datetime.now()

    session.add(user_role)
    session.add(driver_info)
    session.commit()
    session.refresh(user_role)
    session.refresh(driver_info)

    # Enviar notificación de aprobación manual
    notification_service = NotificationService(session)
    notification_result = notification_service.notify_verification_manual_approved(
        user_uuid)

    return {
        "message": "Driver manually approved",
        "user_id": str(user_uuid),
        "new_status": {
            "is_verified": user_role.is_verified,
            "status": user_role.status,
            "verified_at": user_role.verified_at.isoformat() if user_role.verified_at else None
        },
        "verification_status": driver_info.document_verification_status,
        "notification_result": notification_result
    }


@router.post("/manual-reject-driver/{user_id}")
def manual_reject_driver(
    user_id: str,
    session: SessionDep,
    reason: str = Query(None, description="Razón del rechazo manual"),
    current_admin=Depends(get_current_admin_user)
):
    """
    Rechazar manualmente un conductor después de revisión administrativa.
    Envía notificación de rechazo al conductor.
    """
    from uuid import UUID
    from sqlmodel import select
    from app.models.user_has_roles import UserHasRole, RoleStatus
    from app.models.driver_info import DriverInfo
    from app.services.notification_service import NotificationService

    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Buscar el UserHasRole del conductor
    user_role = session.exec(
        select(UserHasRole).where(
            UserHasRole.id_user == user_uuid,
            UserHasRole.id_rol == "DRIVER"
        )
    ).first()

    if not user_role:
        raise HTTPException(status_code=404, detail="Driver role not found")

    # Buscar DriverInfo
    driver_info = session.exec(
        select(DriverInfo).where(DriverInfo.user_id == user_uuid)
    ).first()

    if not driver_info:
        raise HTTPException(status_code=404, detail="DriverInfo not found")

    # Rechazar conductor
    user_role.is_verified = False
    # Mantener en PENDING para que pueda corregir
    user_role.status = RoleStatus.PENDING

    # Actualizar estado de verificación en DriverInfo
    driver_info.document_verification_status = "REJECTED"
    driver_info.document_verification_date = datetime.now()

    session.add(user_role)
    session.add(driver_info)
    session.commit()
    session.refresh(user_role)
    session.refresh(driver_info)

    # Enviar notificación de rechazo manual
    notification_service = NotificationService(session)
    notification_result = notification_service.notify_verification_manual_rejected(
        user_uuid, reason)

    return {
        "message": "Driver manually rejected",
        "user_id": str(user_uuid),
        "new_status": {
            "is_verified": user_role.is_verified,
            "status": user_role.status
        },
        "verification_status": driver_info.document_verification_status,
        "rejection_reason": reason,
        "notification_result": notification_result
    }

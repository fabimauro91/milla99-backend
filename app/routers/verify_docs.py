from fastapi import APIRouter, Depends, status, Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Dict, Any

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


bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/verify-docs",
                   tags=["ADMIN"],
                   dependencies=[Depends(get_current_admin)])


def get_verify_docs_service(session: SessionDep) -> VerifyDocsService:
    """Dependency para obtener el servicio de verificación de documentos"""
    return VerifyDocsService(session)


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
       Si estan vencidas, el estado camvia a espirado """
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

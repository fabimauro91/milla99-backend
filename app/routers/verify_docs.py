from fastapi import APIRouter, Depends, status, Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List

from app.core.dependencies.admin_auth import get_current_admin
from app.models.user import UserRead
from app.models.driver_documents import DocumentsUpdate, DriverDocuments
from app.core.db import SessionDep
from app.services.verify_docs_service import VerifyDocsService, UserWithDocs, UserWithExpiringDocsResponse
from app.core.dependencies.admin_auth import get_current_admin


bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/verify-docs",
                   tags=["ADMIN: document verification"],
                    dependencies=[Depends(get_current_admin)])


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


@router.post("/update-role-status")
def update_role_status(
    request: Request,
    session: SessionDep
):
    """
    Actualiza el estado del rol de los usuarios basado en el estado de sus documentos.
    Si algún documento no está aprobado, el rol del usuario queda como pendiente.

    **Respuesta:**
    Devuelve un mensaje indicando el resultado de la actualización de roles.
    """
    service = VerifyDocsService(session)
    return service.update_user_role_status()


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
            "status": "pending",                                opcional
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

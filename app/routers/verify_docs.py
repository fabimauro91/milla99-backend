from fastapi import APIRouter, Depends, status, Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List

from app.core.dependencies.auth import user_is_owner
from app.models.user import UserRead
from app.models.driver_documents import DriverDocuments
from app.core.db import SessionDep
from app.services.verify_docs_service import VerifyDocsService



router = APIRouter(prefix="/verify-docs", tags=["document verification"])

@router.get("/pending", response_model=List[UserRead])
def get_users_with_pending_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con documentos pendientes"""
    service = VerifyDocsService(session)
    return service.get_users_with_pending_docs()

@router.get("/approved", response_model=List[UserRead])
def get_users_with_all_approved_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con todos los documentos aprobados"""
    service = VerifyDocsService(session)
    return service.get_users_with_all_approved_docs()

@router.get("/rejected", response_model=List[UserRead])
def get_users_with_rejected_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con documentos rechazados"""
    service = VerifyDocsService(session)
    return service.get_users_with_rejected_docs()

@router.get("/expired", response_model=List[UserRead])
def get_users_with_expired_docs(
    request: Request,
    session: SessionDep
):
    """Obtiene usuarios con documentos expirados"""
    service = VerifyDocsService(session)
    return service.get_users_with_expired_docs()

@router.post("/check-expired", status_code=status.HTTP_200_OK)
def update_expired_documents(
    request: Request,
    session: SessionDep
):
    """Actualiza el estado de documentos expirados"""
    service = VerifyDocsService(session)
    updated_count = service.update_expired_documents()
    return {"message": f"Updated {updated_count} expired documents"}

@router.get("/check-expiring-soon", status_code=status.HTTP_200_OK)
def check_soon_to_expire_documents(
    request: Request,
    session: SessionDep
):
    """Verifica documentos próximos a expirar"""
    service = VerifyDocsService(session)
    warnings = service.check_soon_to_expire_documents()
    return {"warnings": warnings}

@router.put("/update-documents", status_code=status.HTTP_200_OK)
def update_documents(
    updates: List[dict],
    request: Request,
    session: SessionDep
):
    """Actualiza múltiples documentos"""
    service = VerifyDocsService(session)
    try:
        updated_docs = service.update_documents(updates)
        return {"message": f"Updated {len(updated_docs)} documents"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
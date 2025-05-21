from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.models.verify_mount import (
    VerifyMount,
    VerifyMountCreate,
    VerifyMountUpdate,
    VerifyMountStatus,
    PaymentMethod
)
from app.services.verify_mount_service import VerifyMountService
from app.core.db import get_session as get_db

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/verify-mounts",
    tags=["verify-mounts"],
    dependencies=[Security(bearer_scheme)]
)


@router.post("/", response_model=VerifyMount)
async def create_verify_mount(
    request: Request,
    verify_mount: VerifyMountCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva solicitud de verificación de monto."""
    service = VerifyMountService(db)
    return service.create_verify_mount(verify_mount, request.state.user_id)


@router.get("/{verify_mount_id}", response_model=VerifyMount)
async def get_verify_mount(
    request: Request,
    verify_mount_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene una verificación de monto específica por su ID."""
    service = VerifyMountService(db)
    verify_mount = service.get_verify_mount(verify_mount_id)

    # Verificar permisos
    if not request.state.is_admin and verify_mount.id_user != request.state.user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this verify mount")

    return verify_mount


@router.get("/", response_model=List[VerifyMount])
async def get_verify_mounts(
    request: Request,
    user_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    status: Optional[VerifyMountStatus] = None,
    payment_method: Optional[PaymentMethod] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtiene una lista de verificaciones de monto con filtros opcionales."""
    # Si no es admin, solo puede ver sus propias verificaciones
    if not request.state.is_admin:
        user_id = request.state.user_id

    service = VerifyMountService(db)
    return service.get_verify_mounts(
        user_id=user_id,
        payment_id=payment_id,
        status=status,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )


@router.patch("/{verify_mount_id}", response_model=VerifyMount)
async def update_verify_mount(
    request: Request,
    verify_mount_id: int,
    verify_mount_update: VerifyMountUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza una verificación de monto existente."""
    service = VerifyMountService(db)
    return service.update_verify_mount(
        verify_mount_id,
        verify_mount_update,
        request.state.user_id
    )


@router.get("/pending/", response_model=List[VerifyMount])
async def get_pending_verify_mounts(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtiene las verificaciones de monto pendientes."""
    if not request.state.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can view pending verify mounts")

    service = VerifyMountService(db)
    return service.get_pending_verify_mounts(skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=List[VerifyMount])
async def get_user_verify_mounts(
    request: Request,
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtiene las verificaciones de monto de un usuario específico."""
    # Verificar permisos
    if not request.state.is_admin and request.state.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view these verify mounts")

    service = VerifyMountService(db)
    return service.get_user_verify_mounts(user_id, skip=skip, limit=limit)

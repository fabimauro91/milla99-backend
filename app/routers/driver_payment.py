from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.models.driver_payment import (
    DriverPayment,
    DriverPaymentCreate,
    DriverPaymentUpdate,
    PaymentStatus
)
from app.models.driver_transaction import DriverTransaction
from app.services.driver_payment_service import DriverPaymentService
from app.core.db import get_session as get_db

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/api/driver-payments",
    tags=["driver-payments"],
    dependencies=[Security(bearer_scheme)]
)


@router.post("/", response_model=DriverPayment)
async def create_payment(
    request: Request,
    payment: DriverPaymentCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva cuenta de pago para un conductor."""
    user_id = request.state.user_id
    if not request.state.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can create payment accounts")

    service = DriverPaymentService(db)
    return service.create_payment(payment, user_id)


@router.get("/{payment_id}", response_model=DriverPayment)
async def get_payment(
    request: Request,
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene una cuenta de pago específica por su ID."""
    service = DriverPaymentService(db)
    payment = service.get_payment(payment_id)

    # Verificar permisos
    if not request.state.is_admin and payment.id_user != request.state.user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this payment account")

    return payment


@router.get("/", response_model=List[DriverPayment])
async def get_payments(
    request: Request,
    user_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtiene una lista de cuentas de pago con filtros opcionales."""
    # Si no es admin, solo puede ver su propia cuenta
    if not request.state.is_admin:
        user_id = request.state.user_id

    service = DriverPaymentService(db)
    return service.get_payments(
        user_id=user_id,
        status=status,
        skip=skip,
        limit=limit
    )


@router.patch("/{payment_id}", response_model=DriverPayment)
async def update_payment(
    request: Request,
    payment_id: int,
    payment_update: DriverPaymentUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza una cuenta de pago existente."""
    service = DriverPaymentService(db)
    return service.update_payment(
        payment_id,
        payment_update,
        request.state.user_id
    )


@router.get("/user/{user_id}", response_model=DriverPayment)
async def get_user_payment(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene la cuenta de pago de un usuario específico."""
    # Verificar permisos
    if not request.state.is_admin and request.state.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this payment account")

    service = DriverPaymentService(db)
    payment = service.get_user_payment(user_id)
    if not payment:
        raise HTTPException(
            status_code=404, detail="Payment account not found")
    return payment


@router.get("/{payment_id}/summary", response_model=dict)
async def get_payment_summary(
    request: Request,
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene un resumen de la cuenta de pago con totales por tipo de transacción."""
    service = DriverPaymentService(db)
    payment = service.get_payment(payment_id)

    # Verificar permisos
    if not request.state.is_admin and payment.id_user != request.state.user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this payment summary")

    return service.get_payment_summary(payment_id)


@router.post("/{payment_id}/welcome-bonus", response_model=DriverTransaction)
async def add_welcome_bonus(
    request: Request,
    payment_id: int,
    bonus_amount: Decimal = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Agrega un bono de bienvenida a la cuenta de pago."""
    service = DriverPaymentService(db)
    return service.add_welcome_bonus(payment_id, bonus_amount, request.state.user_id)

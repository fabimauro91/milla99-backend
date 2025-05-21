from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
import traceback

from app.models.driver_payment import (
    DriverPayment,
    DriverPaymentCreate,
    DriverPaymentUpdate,
    PaymentStatus
)
from app.models.driver_transaction import DriverTransaction
from app.services.driver_payment_service import DriverPaymentService
from app.core.db import get_session as get_db
from app.models.user_has_roles import UserHasRole, RoleStatus

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/driver-payments",
    tags=["driver-payments"],
    dependencies=[Security(bearer_scheme)]
)

# For administrators only, for exceptional cases and testing


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


@router.get("/me", response_model=dict)
async def get_my_payment(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user_id = request.state.user_id
        print(f"[DEBUG] user_id from token: {user_id}")

        # Verificar si el usuario tiene el rol DRIVER aprobado
        user_role = db.exec(
            select(UserHasRole)
            .where(UserHasRole.id_user == user_id)
            .where(UserHasRole.id_rol == "DRIVER")
            .where(UserHasRole.status == RoleStatus.APPROVED)
        ).first()

        if not user_role:
            raise HTTPException(
                status_code=403,
                detail="You do not have the DRIVER role approved. Only drivers have a payment account."
            )

        # Buscar la cuenta de pago
        payment = db.exec(
            select(DriverPayment).where(DriverPayment.id_user == user_id)
        ).first()

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="No payment account found for this driver."
            )

        # Devolver solo los saldos relevantes
        return {
            "total_balance": payment.total_balance,
            "available_balance": payment.available_balance,
            "withdrawable_balance": payment.withdrawable_balance
        }

    except Exception as e:
        print("[ERROR] Exception in get_my_payment:", str(e))
        print(traceback.format_exc())
        raise


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
    try:
        print(f"[DEBUG] user_id from path: {user_id}")
        print(
            f"[DEBUG] request.state.user_id: {getattr(request.state, 'user_id', None)}")
        print(
            f"[DEBUG] request.state.is_admin: {getattr(request.state, 'is_admin', None)}")
        service = DriverPaymentService(db)
        # Lógica de permisos
        if not request.state.is_admin and request.state.user_id != user_id:
            print("[DEBUG] Permiso denegado: usuario no es admin ni dueño de la cuenta")
            raise HTTPException(
                status_code=403, detail="No permission to view this payment account")
        payment = service.get_user_payment(user_id)
        if not payment:
            print("[DEBUG] No se encontró la cuenta de pago para el usuario")
            raise HTTPException(
                status_code=404, detail="Payment account not found")
        return payment
    except Exception as e:
        print("[ERROR] Exception in get_user_payment:", str(e))
        print(traceback.format_exc())
        raise


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

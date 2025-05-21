from typing import List, Optional
from datetime import datetime
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.models.driver_transaction import (
    DriverTransaction,
    DriverTransactionCreate,
    DriverTransactionUpdate,
    DriverTransactionResponse,
    TransactionType,
    TransactionStatus,
    DriverTransactionCreateRequest
)
from app.models.driver_payment import DriverPayment
from app.models.verify_mount import VerifyMount
from app.services.driver_transaction_service import DriverTransactionService
from app.core.db import get_session as get_db

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/driver-transactions",
    tags=["driver-transactions"],
    dependencies=[Security(bearer_scheme)]
)


@router.post("/", response_model=DriverTransactionResponse)
async def create_transaction(
    request: Request,
    transaction: DriverTransactionCreateRequest,
    db: Session = Depends(get_db)
):
    """Crea una nueva transacción para un conductor."""
    user_id = request.state.user_id
    # Buscar la cuenta de pago del usuario
    payment = db.exec(
        select(DriverPayment).where(DriverPayment.id_user == user_id)
    ).first()
    if not payment:
        raise HTTPException(
            status_code=404, detail="Payment account not found for this user.")

    service = DriverTransactionService(db)
    transaction_obj = service.create_transaction(
        id_payment=payment.id,
        id_user=user_id,
        transaction_type=transaction.transaction_type,
        amount=transaction.amount,
        description=transaction.description,
        discount_amount=getattr(transaction, "discount_amount", 0),
        reference_id=getattr(transaction, "reference_id", None),
        id_verify_mount=getattr(transaction, "id_verify_mount", None),
        transaction_date=getattr(transaction, "transaction_date", None)
    )

    # Buscar la verify_mount asociada si existe
    verify_mount = None
    if transaction_obj.id_verify_mount:
        verify_mount = db.get(VerifyMount, transaction_obj.id_verify_mount)
    return DriverTransactionResponse.from_transaction(transaction_obj, verify_mount)


# @router.get("/{transaction_id}", response_model=DriverTransactionResponse)
# async def get_transaction(
#     request: Request,
#     transaction_id: int,
#     db: Session = Depends(get_db)
# ):
#     """Obtiene una transacción específica por su ID."""
#     service = DriverTransactionService(db)
#     transaction = service.get_transaction(transaction_id)

#     # Verificar permisos
#     if not request.state.is_admin and transaction.id_user != request.state.user_id:
#         raise HTTPException(
#             status_code=403, detail="Not authorized to view this transaction")

#     return DriverTransactionResponse.from_transaction(transaction)


# @router.get("/", response_model=List[DriverTransactionResponse])
# async def get_transactions(
#     request: Request,
#     user_id: Optional[int] = None,
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=100),
#     db: Session = Depends(get_db)
# ):
#     """Obtiene una lista de transacciones con filtros opcionales."""
#     # Si no es admin, solo puede ver sus propias transacciones
#     if not request.state.is_admin:
#         user_id = request.state.user_id

#     service = DriverTransactionService(db)
#     return service.get_transactions(
#         user_id=user_id,
#         skip=skip,
#         limit=limit
#     )


# @router.get("/user/{user_id}", response_model=List[DriverTransactionResponse])
# async def get_user_transactions(
#     request: Request,
#     user_id: int,
#     skip: int = Query(0, ge=0),
#     limit: int = Query(100, ge=1, le=100),
#     db: Session = Depends(get_db)
# ):
#     """Obtiene las transacciones de un usuario específico."""
#     # Verificar permisos
#     if not request.state.is_admin and request.state.user_id != user_id:
#         raise HTTPException(
#             status_code=403, detail="Not authorized to view these transactions")

#     service = DriverTransactionService(db)
#     return service.get_user_transactions(user_id, skip=skip, limit=limit)


# @router.patch("/{transaction_id}", response_model=DriverTransactionResponse)
# async def update_transaction(
#     request: Request,
#     transaction_id: int,
#     transaction_update: DriverTransactionUpdate,
#     db: Session = Depends(get_db)
# ):
#     """Actualiza una transacción existente."""
#     try:
#         service = DriverTransactionService(db)
#         updated_transaction = service.update_transaction(
#             transaction_id,
#             transaction_update,
#             request.state.user_id
#         )
#         return DriverTransactionResponse.from_transaction(updated_transaction)
#     except Exception as e:
#         print("Error en update_transaction:")
#         print(traceback.format_exc())
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error al actualizar la transacción: {str(e)}"
#         )


# @router.get("/summary/", response_model=dict)
# async def get_transaction_summary(
#     request: Request,
#     user_id: Optional[int] = None,
#     payment_id: Optional[int] = None,
#     start_date: Optional[datetime] = None,
#     end_date: Optional[datetime] = None,
#     db: Session = Depends(get_db)
# ):
#     """Obtiene un resumen de las transacciones con totales por tipo."""
#     try:
#         # Si no es admin, solo puede ver sus propios resúmenes
#         if not request.state.is_admin:
#             user_id = request.state.user_id

#         service = DriverTransactionService(db)
#         return service.get_transaction_summary(
#             user_id=user_id,
#             payment_id=payment_id,
#             start_date=start_date,
#             end_date=end_date
#         )
#     except Exception as e:
#         print("Error en get_transaction_summary:")
#         print(traceback.format_exc())
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error al obtener el resumen de transacciones: {str(e)}"
#         )

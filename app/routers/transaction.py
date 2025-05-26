from fastapi import APIRouter, Depends, Request
from app.core.db import SessionDep
from app.services.transaction_service import TransactionService
from app.models.transaction import TransactionType, TransactionCreate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", description="Crea una transacción para el usuario autenticado.")
def create_transaction(
    request: Request,
    session: SessionDep,
    data: TransactionCreate
):
    user_id = request.state.user_id
    return TransactionService(session).create_transaction(
        user_id,
        income=data.income,
        expense=data.expense,
        type=data.type,
        client_request_id=data.client_request_id
    )


@router.get("/balance/me", description="Consulta el saldo (available, withdrawable y mount) del usuario autenticado.")
def get_my_balance(request: Request, session: SessionDep):
    user_id = request.state.user_id  # <-- lo tomas del token
    service = TransactionService(session)
    return service.get_user_balance(user_id)


@router.get("/list/me", description="Lista todas las transacciones del usuario autenticado.")
def list_my_transactions(request: Request, session: SessionDep):
    user_id = request.state.user_id  # <-- lo tomas del token
    service = TransactionService(session)
    return service.list_transactions(user_id)

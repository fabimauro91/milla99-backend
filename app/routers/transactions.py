from fastapi import APIRouter, Query, status
from app.models import Transaction, TransactionCreate
from app.core.db import SessionDep
from app.services.transaction_service import TransactionService

router = APIRouter()

@router.post("/transactions", status_code=status.HTTP_201_CREATED, tags=["transactions"])
async def create_transaction(transaction_data: TransactionCreate, session: SessionDep):
    service = TransactionService(session)
    return service.create_transaction(transaction_data)

@router.get("/transactions", tags=["transactions"])
async def list_transactions(
    session: SessionDep, 
    skip: int = Query(0, description="Registros a omitir"), 
    limit: int = Query(10, description="Numero de registros a retornar")
):
    service = TransactionService(session)
    return service.get_transactions(skip, limit)


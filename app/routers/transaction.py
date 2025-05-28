from fastapi import APIRouter, Depends, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.db import SessionDep
from app.services.transaction_service import TransactionService
from app.models.transaction import TransactionType, TransactionCreate

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/transactions", tags=["transactions"])

bearer_scheme = HTTPBearer()



@router.get("/balance/me", description="Consulta el saldo (available, withdrawable y mount) del usuario autenticado.")
def get_my_balance(request: Request,
                    session: SessionDep,
                    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
                    ):
    user_id = request.state.user_id  # <-- lo tomas del token
    service = TransactionService(session)
    return service.get_user_balance(user_id)





@router.get("/list/me", description="Lista todas las transacciones del usuario autenticado.")
def list_my_transactions(request: Request,
                        session: SessionDep,
                        credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
                        ):
    user_id = request.state.user_id  # <-- lo tomas del token
    service = TransactionService(session)
    return service.list_transactions(user_id)

from fastapi import APIRouter, Depends, HTTPException, status, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from app.core.db import get_session
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.utils.withdrawal_utils import assert_can_withdraw, InsufficientFundsException
from app.services.withdrawal_service import WithdrawalService
from pydantic import BaseModel
from uuid import UUID
from app.services.bank_account_service import BankAccountService
from app.models.bank_account import BankAccountRead

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])
bearer_scheme = HTTPBearer()


class WithdrawalRequest(BaseModel):
    amount: int
    bank_account_id: UUID


class WithdrawalIdRequest(BaseModel):
    withdrawal_id: int


class WithdrawalStatusUpdateRequest(BaseModel):
    withdrawal_id: int
    status: str  # 'approved' o 'rejected'


@router.post("/", status_code=status.HTTP_201_CREATED)
def request_withdrawal(
    request: Request,
    data: WithdrawalRequest,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Permite al usuario autenticado solicitar un retiro. 
    Al solicitar el retiro:
    1. Se verifica el saldo
    2. Se verifica la cuenta bancaria
    3. Se descuenta el monto inmediatamente
    4. Se crea la transacción con is_confirmed=True
    5. Se crea el retiro en estado PENDING asociado a la cuenta bancaria
    """
    user_id = request.state.user_id
    service = WithdrawalService(session)
    return service.request_withdrawal(user_id, data.amount, data.bank_account_id)


@router.get("/me", response_model=list[Withdrawal])
def list_my_withdrawals(
    request: Request,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Devuelve el historial de retiros del usuario autenticado.
    """
    user_id = request.state.user_id
    withdrawals = session.query(Withdrawal).filter(
        Withdrawal.user_id == user_id).order_by(Withdrawal.withdrawal_date.desc()).all()
    return withdrawals


@router.get("/available-accounts", response_model=list[BankAccountRead])
def get_available_bank_accounts(
    request: Request,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Devuelve las cuentas bancarias activas del usuario que pueden ser usadas para retiros.
    """
    user_id = request.state.user_id
    service = BankAccountService(session)
    return service.get_active_bank_accounts(user_id)

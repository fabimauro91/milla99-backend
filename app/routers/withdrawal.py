from fastapi import APIRouter, Depends, HTTPException, status, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from app.core.db import get_session
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.utils.withdrawal_utils import assert_can_withdraw, InsufficientFundsException
from app.services.withdrawal_service import WithdrawalService
from pydantic import BaseModel

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])
bearer_scheme = HTTPBearer()


class WithdrawalRequest(BaseModel):
    amount: int


class WithdrawalIdRequest(BaseModel):
    withdrawal_id: int


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
    2. Se descuenta el monto inmediatamente
    3. Se crea la transacción con is_confirmed=True
    4. Se crea el retiro en estado PENDING
    """
    user_id = request.state.user_id
    service = WithdrawalService(session)
    return service.request_withdrawal(user_id, data.amount)


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


@router.patch("/approve")
def approve_withdrawal(
    data: WithdrawalIdRequest,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Aprueba un retiro (en el futuro, solo admin podrá usarlo).
    """
    service = WithdrawalService(session)
    return service.approve_withdrawal(data.withdrawal_id)


@router.patch("/reject")
def reject_withdrawal(
    data: WithdrawalIdRequest,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Rechaza un retiro (en el futuro, solo admin podrá usarlo).
    """
    service = WithdrawalService(session)
    return service.reject_withdrawal(data.withdrawal_id)

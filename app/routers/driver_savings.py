from fastapi import APIRouter, Depends, Request, Security, status, Body
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from app.core.db import get_session
from app.services.driver_savings_service import DriverSavingsService
from app.core.dependencies.auth import get_current_user

router = APIRouter(prefix="/driver-savings", tags=["driver-savings"])
bearer_scheme = HTTPBearer()


@router.get("/me")
def get_my_driver_savings(
    request: Request,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Devuelve el estado del ahorro del conductor autenticado, incluyendo si puede retirar y días restantes.
    """
    user_id = request.state.user_id
    service = DriverSavingsService(session)
    return service.get_driver_savings_status(user_id)


@router.post("/transfer_saving_to_balance", status_code=status.HTTP_200_OK)
def transfer_saving_to_balance(
    request: Request,
    amount: float = Body(..., embed=True,
                         description="Monto a transferir del ahorro al balance"),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Transfiere dinero del ahorro al balance del conductor.
    - El monto mínimo es 50,000
    - Solo conductores aprobados pueden transferir
    - El saldo en ahorro debe ser suficiente
    """
    user_id = request.state.user_id
    service = DriverSavingsService(session)
    return service.transfer_saving_to_balance(user_id, amount)

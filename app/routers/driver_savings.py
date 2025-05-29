from fastapi import APIRouter, Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from app.core.db import get_session
from app.services.driver_savings_service import DriverSavingsService

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


@router.post("/withdraw")
def withdraw_my_savings(
    request: Request,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    Permite al conductor retirar la totalidad de su ahorro si ha pasado 1 año desde la primera ganancia.
    """
    user_id = request.state.user_id
    service = DriverSavingsService(session)
    return service.withdraw_savings(user_id)

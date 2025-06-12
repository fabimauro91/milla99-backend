from fastapi import APIRouter, Depends, HTTPException, status, Request, Security, Body, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from app.core.db import get_session
from app.models.bank_account import (
    BankAccount, BankAccountCreate, BankAccountRead, AccountType, BankAccountUpdate
)
from app.services.bank_account_service import BankAccountService
from typing import List, Optional
from uuid import UUID
from app.core.dependencies.auth import get_current_user

router = APIRouter(prefix="/bank-accounts", tags=["bank-accounts"])
bearer_scheme = HTTPBearer()


@router.post("/", response_model=BankAccountRead, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    request: Request,
    bank_account: BankAccountCreate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Crea una nueva cuenta bancaria para el usuario autenticado.
    Los datos sensibles (número de cuenta y cédula) se encriptan antes de guardar.
    Solo usuarios aprobados (clientes o conductores) pueden crear cuentas.
    Requiere: bank_id, type_identification, account_type, account_holder_name, account_number, identification_number
    """
    user_id = request.state.user_id
    service = BankAccountService(session)
    return service.create_bank_account(user_id, bank_account)


@router.get("/me", response_model=List[BankAccountRead])
def list_my_bank_accounts(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Lista todas las cuentas bancarias del usuario autenticado.
    Los datos sensibles se devuelven enmascarados.
    Solo usuarios aprobados (clientes o conductores) pueden ver sus cuentas.
    """
    user_id = request.state.user_id
    service = BankAccountService(session)
    return service.get_bank_accounts(user_id)


# @router.get("/{account_id}", response_model=BankAccountRead)
# def get_bank_account(
#     request: Request,
#     account_id: UUID,
#     session: Session = Depends(get_session),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Obtiene los detalles de una cuenta bancaria específica.
#     Verifica que la cuenta pertenezca al usuario autenticado.
#     Los datos sensibles se devuelven enmascarados.
#     """
#     user_id = request.state.user_id
#     service = BankAccountService(session)
#     return service.get_bank_account(user_id, account_id)


@router.patch("/{account_id}", response_model=BankAccountRead)
def patch_bank_account(
    request: Request,
    account_id: UUID,
    update_data: BankAccountUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    try:
        print(f"PATCH request received for account_id: {account_id}")
        user_id = request.state.user_id
        print(f"User ID: {user_id}")

        update_dict = update_data.dict(exclude_unset=True)
        print(f"Filtered update data: {update_dict}")

        service = BankAccountService(session)
        return service.update_bank_account(user_id, account_id, update_dict)
    except Exception as e:
        print(f"Error in patch_bank_account: {str(e)}")
        raise


@router.delete("/{account_id}")
def delete_bank_account(
    request: Request,
    account_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Desactiva una cuenta bancaria.
    No permite eliminar si hay retiros pendientes o recientes.
    """
    user_id = request.state.user_id
    service = BankAccountService(session)
    return service.delete_bank_account(user_id, account_id)


# @router.get("/active", response_model=List[BankAccountRead])
# def list_active_bank_accounts(
#     request: Request,
#     session: Session = Depends(get_session),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Lista solo las cuentas bancarias activas del usuario autenticado.
#     Los datos sensibles se devuelven enmascarados.
#     """
#     user_id = request.state.user_id
#     service = BankAccountService(session)
#     return service.get_active_bank_accounts(user_id)


# @router.get("/verified", response_model=List[BankAccountRead])
# def list_verified_bank_accounts(
#     request: Request,
#     session: Session = Depends(get_session),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Lista solo las cuentas bancarias verificadas del usuario autenticado.
#     Los datos sensibles se devuelven enmascarados.
#     """
#     user_id = request.state.user_id
#     service = BankAccountService(session)
#     return service.get_verified_bank_accounts(user_id)
